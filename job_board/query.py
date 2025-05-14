from datetime import datetime
from decimal import Decimal

from sqlalchemy import any_
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select

from job_board.base import Job as JobListing
from job_board.connection import get_session
from job_board.models import Job
from job_board.models import JobTag
from job_board.models import Tag


def count_jobs(
    tags: list[str],
    salary: Decimal,
    is_remote: bool = True,
    posted_on: datetime | None = None,
):
    statement = (
        select(func.count(Job.id))
        .select_from(Job)
        .join(JobTag, JobTag.job_id == Job.id)
        .join(Tag, JobTag.tag_id == Tag.id)
        .where(
            Job.is_active.is_(True),
            Job.is_remote.is_(is_remote),
            Job.salary >= salary,
            or_(
                not tags,
                Tag.name.ilike(any_(tags)),
            ),
        )
    )

    with get_session(readonly=True) as session:
        result = session.execute(statement)
        count = result.scalar_one()

    return count


def filter_jobs(
    tags: list[str],
    salary: Decimal,
    is_remote: bool = True,
    posted_on: datetime | None = None,
    offset: int = 0,
    limit: int = 10,
):
    statement = (
        (
            select(Job)
            .join(JobTag, JobTag.job_id == Job.id)
            .join(Tag, JobTag.tag_id == Tag.id)
            .where(
                Job.is_active.is_(True),
                Job.is_remote.is_(is_remote),
                Job.salary >= salary,
                or_(
                    not tags,
                    Tag.name.ilike(any_(tags)),
                ),
            )
        )
        .order_by(
            Job.salary.desc(),
            Job.posted_on.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    with get_session(readonly=True) as session:
        result = session.execute(statement)
        job_objs = result.scalars().all()
        jobs = [
            JobListing(
                title=job.title,
                description=job.description,
                link=job.link,
                salary=job.salary,
                posted_on=job.posted_on,
                tags=[tag.name for tag in job.tags],
                is_remote=job.is_remote,
                # locations=job.locations,
            )
            for job in job_objs
        ]

    return jobs
