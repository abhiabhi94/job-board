import itertools

from requests.structures import CaseInsensitiveDict
from sqlalchemy import any_
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import func
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import select
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression

from job_board.base import Job as JobListing
from job_board.connection import get_session
from job_board.logger import logger
from job_board.utils import utcnow_naive


# Base class for all models
class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(
        DateTime,
        default=utcnow_naive,
        nullable=False,
        server_default=func.now(),
    )
    edited_at = Column(
        DateTime,
        default=utcnow_naive,
        onupdate=utcnow_naive,
        server_default=func.now(),
        nullable=False,
    )


class JobTag(BaseModel):
    __tablename__ = "job_tag"

    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tag.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "tag_id",
            name="uq_job_tag_job_id_tag_id",
        ),
    )


class Tag(BaseModel):
    __tablename__ = "tag"

    name = Column(String, nullable=False)
    jobs = relationship(
        "Job",
        secondary=JobTag.__table__,
        back_populates="tags",
        lazy="selectin",
    )

    __table_args__ = (
        Index(
            "ix_tag_name_lower",
            func.lower(name),
            unique=True,
        ),
    )


class Job(BaseModel):
    __tablename__ = "job"

    is_active = Column(
        Boolean,
        default=True,
        server_default=expression.true(),
        nullable=False,
        index=True,
    )
    link = Column(String, nullable=False)
    title = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    salary = Column(Numeric, nullable=True, index=True)
    posted_on = Column(
        DateTime,
        default=utcnow_naive,
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    tags = relationship(
        "Tag",
        secondary=JobTag.__table__,
        back_populates="jobs",
        lazy="selectin",
    )
    is_remote = Column(
        Boolean,
        default=False,
        server_default=expression.false(),
        index=True,
    )
    # FIXME: find a way to make this more uniform.
    # locations = Column(String, nullable=True)

    __table_args__ = (
        Index(
            "ix_job_link_lower",
            func.lower(link),
            unique=True,
        ),
        Index(
            "ix_job_title_lower",
            func.lower(title),
        ),
    )


def store_jobs(jobs: JobListing):
    if not jobs:
        logger.debug("No jobs to store")
        return

    with get_session(readonly=False) as session:
        _store_jobs(session=session, jobs=jobs)


def _store_jobs(session, jobs: JobListing):
    tags = set()
    for job in jobs:
        if _tags := job.tags:
            tags.update(_tags)

    for batch in itertools.batched(tags, 1_000):
        # insert the tags in batches of 1000
        # to avoid hitting the max number of parameters
        # in a single query
        session.execute(
            insert(Tag)
            .values([{"name": t} for t in batch])
            .on_conflict_do_nothing(
                index_elements=[
                    func.lower(Tag.name),
                ],
            )
        )
    existing_tags = (
        session.execute(select(Tag).where(Tag.name.ilike(any_(list(tags)))))
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

    job_link_map = CaseInsensitiveDict()
    for batch in itertools.batched(values, 1_000):
        # insert the jobs in batches of 1000
        # to avoid hitting the max number of parameters
        # in a single query
        job_ids = (
            session.execute(
                insert(Job)
                .values(batch)
                .on_conflict_do_nothing(
                    index_elements=[
                        func.lower(Job.link),
                    ],
                )
                .returning(Job.id)
            )
            .scalars()
            .all()
        )

        # now associate the jobs with the tags
        job_objs = (
            session.execute(select(Job).where(Job.id.in_(job_ids))).scalars().all()
        )

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

    for batch in itertools.batched(job_tags, 1_000):
        session.execute(
            insert(JobTag)
            .values(batch)
            .on_conflict_do_nothing(
                index_elements=[
                    JobTag.job_id,
                    JobTag.tag_id,
                ],
            )
        )

    logger.debug(f"Stored {len(job_link_map)} new jobs successfully")
