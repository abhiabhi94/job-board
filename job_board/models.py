import itertools
from datetime import timedelta

import sqlalchemy as sa
from requests.structures import CaseInsensitiveDict
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression

from job_board import config
from job_board.connection import get_session
from job_board.logger import logger
from job_board.portals.parser import Job as JobListing
from job_board.utils import utcnow_naive


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
    salary = sa.Column(sa.Numeric, nullable=True, index=True)
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
    # FIXME: find a way to make this more uniform.
    # locations = sa.Column(sa.String, nullable=True)

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
    )


class Payload(BaseModel):
    __tablename__ = "payload"

    link = sa.Column(sa.String, nullable=False)
    payload = sa.Column(sa.String, nullable=False)

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
            _store_jobs(session=session, jobs=batch)

    store_payloads(jobs)


def _store_jobs(session, jobs: JobListing):
    tags = set()
    for job in jobs:
        if _tags := job.tags:
            tags.update(_tags)

    if tags:
        session.execute(
            insert(Tag)
            .values([{"name": t} for t in tags])
            .on_conflict_do_nothing(
                index_elements=[
                    sa.func.lower(Tag.name),
                ],
            )
        )
        logger.info("Stored tags")
    else:
        logger.info("No tags to store")

    existing_tags = (
        session.execute(sa.select(Tag).where(Tag.name.ilike(sa.any_(list(tags)))))
        .scalars()
        .all()
    )

    tag_map = CaseInsensitiveDict()
    for tag in existing_tags:
        tag_map[tag.name] = tag.id

    values = []
    for job in jobs:
        value = {
            "link": job.link,
            "title": job.title,
            "salary": job.salary,
            "description": job.description,
            "is_remote": job.is_remote,
            # FIXME: find a way to make this more uniform.
            # "locations": job.locations,
        }
        if posted_on := job.posted_on:
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

    # now associate the jobs with the tags
    job_objs = (
        session.execute(sa.select(Job).where(Job.id.in_(job_ids))).scalars().all()
    )

    job_link_map = CaseInsensitiveDict()
    for job in job_objs:
        job_link_map[job.link] = job.id

    job_tags = []
    for job in jobs:
        job_id = job_link_map.get(job.link)
        if not job_id:
            # the job already exists
            continue
        for tag in job.tags:
            job_tags.append(
                {
                    "job_id": job_id,
                    "tag_id": tag_map[tag],
                }
            )

    if job_tags:
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

    logger.info(f"Stored {len(job_link_map)} new job tag links")


def store_payloads(jobs: JobListing) -> None:
    for batch in itertools.batched(jobs, BATCH_PAYLOAD_SIZE):
        with get_session(readonly=False) as session:
            _store_payloads(session=session, jobs=batch)


def _store_payloads(session, jobs: JobListing) -> None:
    values = []
    for job in jobs:
        value = {
            "link": job.link,
            "payload": job.payload,
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
