from __future__ import annotations

import itertools
from datetime import timedelta

import pycountry
import sqlalchemy as sa
from requests.structures import CaseInsensitiveDict
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression

from job_board import config
from job_board.connection import get_session
from job_board.logger import logger
from job_board.portals.parser import extract_job_tags_using_llm
from job_board.portals.parser import Job as JobListing
from job_board.utils import add_missing_countries
from job_board.utils import utcnow_naive

# TODO: move this to a separate place, this is not the right place for it.
add_missing_countries()
# Generate valid location codes list once
_valid_codes = []
for country in pycountry.countries:
    _valid_codes.append(f"'{country.alpha_2}'::text")
for subdivision in pycountry.subdivisions:
    _valid_codes.append(f"'{subdivision.code}'::text")
_valid_codes_array = "[" + ",".join(_valid_codes) + "]::text[]"


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    created_at = sa.Column(
        sa.DateTime,
        default=utcnow_naive,
        nullable=False,
        server_default=sa.func.now(),
    )
    edited_at = sa.Column(
        sa.DateTime,
        default=utcnow_naive,
        onupdate=utcnow_naive,
        server_default=sa.func.now(),
        nullable=False,
    )


class JobTag(BaseModel):
    __tablename__ = "job_tag"

    job_id: Mapped[int] = mapped_column(
        sa.Integer,
        sa.ForeignKey("job.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tag_id: Mapped[int] = mapped_column(
        sa.Integer,
        sa.ForeignKey("tag.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "job_id",
            "tag_id",
            name="uq_job_tag_job_id_tag_id",
        ),
    )


class Tag(BaseModel):
    __tablename__ = "tag"

    name = sa.Column(sa.String, nullable=False)
    jobs = relationship(
        "Job",
        secondary=JobTag.__table__,
        back_populates="tags",
        lazy="noload",
    )

    __table_args__ = (
        sa.Index(
            "ix_tag_name_lower",
            sa.func.lower(name),
            unique=True,
        ),
    )


class Job(BaseModel):
    __tablename__ = "job"

    is_active = sa.Column(
        sa.Boolean,
        default=True,
        server_default=expression.true(),
        nullable=False,
        index=True,
    )
    link = sa.Column(sa.String, nullable=False)
    title = sa.Column(sa.String, nullable=False)
    description = sa.Column(sa.String, nullable=True)
    min_salary = sa.Column(sa.Numeric, nullable=True, index=True)
    max_salary = sa.Column(sa.Numeric, nullable=True, index=True)
    posted_on = sa.Column(
        sa.DateTime,
        default=utcnow_naive,
        nullable=False,
        server_default=sa.func.now(),
        index=True,
    )
    tags = relationship(
        "Tag",
        secondary=JobTag.__table__,
        back_populates="jobs",
        lazy="selectin",
    )
    is_remote = sa.Column(
        sa.Boolean,
        default=False,
        server_default=expression.false(),
        index=True,
    )
    locations = sa.Column(sa.ARRAY(sa.String), nullable=True)
    # TODO: make this required in future, can't backfill it now
    # for all existing jobs.
    company_name = sa.Column(sa.String, nullable=True)

    __table_args__ = (
        sa.Index(
            "ix_job_link_lower",
            sa.func.lower(link),
            unique=True,
        ),
        sa.Index(
            "ix_job_title_lower",
            sa.func.lower(title),
        ),
        sa.CheckConstraint(
            "min_salary IS NULL OR min_salary >= 0",
            name="check_min_salary_non_negative",
        ),
        sa.CheckConstraint(
            "max_salary IS NULL OR max_salary >= 0",
            name="check_max_salary_non_negative",
        ),
        sa.CheckConstraint(
            "min_salary IS NULL OR max_salary IS NULL OR max_salary >= min_salary",
            name="check_salary_range",
        ),
        sa.CheckConstraint(
            f"locations IS NULL OR locations::text[] <@ ARRAY{_valid_codes_array}",
            name="check_valid_location_codes",
        ),
        sa.Index("ix_job_locations", "locations", postgresql_using="gin"),
    )

    @hybrid_property
    def portal_name(self) -> str | None:
        from job_board.portals.base import PORTALS

        for portal_class in PORTALS.values():
            if self.link.startswith(portal_class.base_url):
                return portal_class.display_name
        return None

    @portal_name.expression
    def portal_name(cls):
        from job_board.portals.base import PORTALS

        case_conditions = []
        for portal_class in PORTALS.values():
            case_conditions.append(
                (cls.link.startswith(portal_class.base_url), portal_class.display_name)
            )

        return sa.case(*case_conditions, else_=None)

    @classmethod
    def fill_missing_tags(cls) -> None:
        with get_session(readonly=True) as session:
            jobs = (
                session.execute(
                    sa.select(Job)
                    .where(Job.is_active.is_(True))
                    .outerjoin(JobTag, Job.id == JobTag.job_id)
                    .where(JobTag.job_id.is_(None))
                )
                .scalars()
                .all()
            )
            job_listings = []
            for job in jobs:
                job_obj = JobListing(
                    title=job.title,
                    description=job.description,
                    link=job.link,
                    tags=[],
                )
                job_listings.append(job_obj)

        if not job_listings:
            logger.info("No jobs found without tags")
            return

        logger.info(f"Found {len(job_listings)} jobs without tags")

        for batch in itertools.batched(job_listings, config.BATCH_TAG_FILLING_SIZE):
            listings_with_tags = extract_job_tags_using_llm(batch)
            with get_session(readonly=False) as session:
                store_tags(session=session, job_listings=listings_with_tags)

            logger.info(f"Processed batch of {len(batch)} jobs")


class Payload(BaseModel):
    __tablename__ = "payload"

    link = sa.Column(sa.String, nullable=False)
    payload = sa.Column(sa.String, nullable=False)
    extra_info = sa.Column(sa.String, nullable=True)

    __table_args__ = (
        sa.Index(
            "ix_payload_link_lower",
            sa.func.lower(link),
            unique=True,
        ),
    )


BATCH_JOB_SIZE = 500
BATCH_PAYLOAD_SIZE = 200


def store_jobs(jobs: JobListing):
    for batch in itertools.batched(jobs, BATCH_JOB_SIZE):
        with get_session(readonly=False) as session:
            _store_jobs(session=session, job_listings=batch)

    store_payloads(jobs)


def _store_jobs(session, job_listings: JobListing) -> None:
    values = []
    for listing in job_listings:
        value = {
            "link": listing.link,
            "title": listing.title,
            "min_salary": listing.min_salary,
            "max_salary": listing.max_salary,
            "description": listing.description,
            "is_remote": listing.is_remote,
            "locations": listing.locations,
            "company_name": listing.company_name,
        }
        if posted_on := listing.posted_on:
            value["posted_on"] = posted_on
        values.append(value)

    job_ids = (
        session.execute(
            insert(Job)
            .values(values)
            .on_conflict_do_nothing(
                index_elements=[
                    sa.func.lower(Job.link),
                ],
            )
            .returning(Job.id)
        )
        .scalars()
        .all()
    )
    logger.info(f"Stored {len(job_ids)} new jobs")
    store_tags(session=session, job_listings=job_listings)


def store_tags(*, session, job_listings: list[JobListing]):
    """Store tags and job-tag relationships for jobs with tags"""
    all_tags = set()
    for listing in job_listings:
        if tags := listing.tags:
            all_tags.update(tags)

    if not all_tags:
        logger.info("No tags to store")
        return

    session.execute(
        insert(Tag)
        .values([{"name": tag} for tag in all_tags])
        .on_conflict_do_nothing(
            index_elements=[
                sa.func.lower(Tag.name),
            ],
        )
    )

    existing_tags = (
        session.execute(sa.select(Tag).where(Tag.name.ilike(sa.any_(list(all_tags)))))
        .scalars()
        .all()
    )

    tag_map = CaseInsensitiveDict()
    for tag in existing_tags:
        tag_map[tag.name] = tag.id

    job_links = [job.link for job in job_listings]
    jobs = (
        session.execute(
            sa.select(Job).where(
                sa.func.lower(Job.link).in_([link.lower() for link in job_links])
            )
        )
        .scalars()
        .all()
    )

    job_link_map = CaseInsensitiveDict()
    for job in jobs:
        job_link_map[job.link] = job.id

    job_tags = []
    for listing in job_listings:
        job_id = job_link_map[listing.link]
        for tag_name in listing.tags:
            tag_id = tag_map[tag_name]
            job_tags.append(
                {
                    "job_id": job_id,
                    "tag_id": tag_id,
                }
            )

    session.execute(
        insert(JobTag)
        .values(job_tags)
        .on_conflict_do_nothing(
            index_elements=[
                JobTag.job_id,
                JobTag.tag_id,
            ],
        )
    )

    logger.info(f"Stored tags for {len(job_listings)} jobs")


def store_payloads(job_listings: JobListing) -> None:
    for batch in itertools.batched(job_listings, BATCH_PAYLOAD_SIZE):
        with get_session(readonly=False) as session:
            _store_payloads(session=session, job_listings=batch)


def _store_payloads(session, job_listings: JobListing) -> None:
    values = []
    for listing in job_listings:
        value = {
            "link": listing.link,
            "payload": listing.payload,
            "extra_info": listing.extra_info,
        }
        values.append(value)

    payload_ids = (
        session.execute(
            insert(Payload)
            .values(values)
            .on_conflict_do_nothing(
                index_elements=[
                    sa.func.lower(Payload.link),
                ],
            )
            .returning(Payload.id)
        )
        .scalars()
        .all()
    )
    logger.info(f"Stored {len(payload_ids)} new payloads")


def purge_old_jobs():
    with get_session(readonly=False) as session:
        deleted_jobs = session.execute(
            sa.delete(Job).where(
                Job.posted_on
                < (utcnow_naive() - timedelta(days=config.JOB_AGE_LIMIT_DAYS))
            )
        )

        deleted_payloads = session.execute(
            sa.delete(Payload).where(
                ~sa.exists(sa.select(Job.id).where(Job.link == Payload.link))
            )
        )
        logger.info(
            f"Purged {deleted_jobs.rowcount} old jobs and "
            f"{deleted_payloads.rowcount} old payloads."
        )
