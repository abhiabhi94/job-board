from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa

from job_board.connection import get_session
from job_board.models import Job
from job_board.models import JobTag
from job_board.models import Tag
from job_board.portals.parser import Job as JobListing


def count_jobs(
    tags: list[str],
    min_salary: Decimal,
    include_no_salary: bool,
    posted_on: datetime,
    is_remote: bool | None,
):
    filters = _get_filters(
        tags=tags,
        min_salary=min_salary,
        include_no_salary=include_no_salary,
        is_remote=is_remote,
        posted_on=posted_on,
    )

    statement = (
        sa.select(sa.func.count(sa.distinct(Job.id)))
        .select_from(Job)
        .join(JobTag, JobTag.job_id == Job.id)
        .join(Tag, JobTag.tag_id == Tag.id)
        .distinct()
        .where(*filters)
    )

    with get_session(readonly=True) as session:
        result = session.execute(statement)
        count = result.scalar_one()

    return count


def filter_jobs(
    tags: list[str],
    min_salary: Decimal,
    include_no_salary: bool,
    is_remote: bool | None,
    posted_on: datetime,
    order_by: sa.UnaryExpression,
    offset: int = 0,
    limit: int = 10,
):
    filters = _get_filters(
        tags=tags,
        min_salary=min_salary,
        include_no_salary=include_no_salary,
        is_remote=is_remote,
        posted_on=posted_on,
    )

    statement = (
        (
            sa.select(Job)
            .join(JobTag, JobTag.job_id == Job.id)
            .join(Tag, JobTag.tag_id == Tag.id)
            .distinct()
            .where(*filters)
        )
        .order_by(order_by)
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


def _get_filters(
    tags: list[str],
    min_salary: Decimal,
    include_no_salary: bool,
    is_remote: bool,
    posted_on: datetime,
):
    filters: list[sa.UnaryExpression] = [
        Job.is_active.is_(True),
        Job.posted_on >= posted_on,
    ]
    if is_remote is not None:  # allow filtering for both remote and non-remote jobs
        filters.append(Job.is_remote == is_remote)

    if include_no_salary:
        filters.append(sa.or_(Job.salary >= min_salary, Job.salary.is_(None)))
    else:
        filters.append(Job.salary >= min_salary)

    if tags:
        # not using any_ directly because it doesn't work with ilike
        # and we need case-insensitive matching
        tag_conditions = [Tag.name.ilike(tag) for tag in tags]
        filters.append(sa.or_(*tag_conditions))

    return filters
