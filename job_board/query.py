from datetime import datetime
from decimal import Decimal

import pycountry
import sqlalchemy as sa

from job_board.connection import get_session
from job_board.models import Job
from job_board.models import JobTag
from job_board.models import Tag
from job_board.portals.parser import Job as JobListing

# Precompute subdivision mappings for efficient location filtering
SUBDIVISION_MAP = {}
for subdivision in pycountry.subdivisions:
    country_code = subdivision.code.split("-")[0]
    if country_code not in SUBDIVISION_MAP:
        SUBDIVISION_MAP[country_code] = []
    SUBDIVISION_MAP[country_code].append(subdivision.code)


def count_jobs(
    tags: list[str],
    min_salary: Decimal,
    include_without_salary: bool,
    posted_on: datetime,
    is_remote: bool | None,
    location_code: str | None = None,
):
    filters = _get_filters(
        tags=tags,
        min_salary=min_salary,
        include_without_salary=include_without_salary,
        is_remote=is_remote,
        posted_on=posted_on,
        location_code=location_code,
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
    include_without_salary: bool,
    is_remote: bool | None,
    posted_on: datetime,
    order_by: sa.UnaryExpression,
    offset: int = 0,
    limit: int = 10,
    location_code: str | None = None,
):
    filters = _get_filters(
        tags=tags,
        min_salary=min_salary,
        include_without_salary=include_without_salary,
        is_remote=is_remote,
        posted_on=posted_on,
        location_code=location_code,
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
        jobs = result.scalars().all()
        job_listings = [
            JobListing(
                title=job.title,
                description=job.description,
                link=job.link,
                min_salary=job.min_salary,
                max_salary=job.max_salary,
                posted_on=job.posted_on,
                tags=[tag.name for tag in job.tags],
                is_remote=job.is_remote,
                locations=job.locations,
                portal_name=job.portal_name,
            )
            for job in jobs
        ]

    return job_listings


def _get_filters(
    tags: list[str],
    min_salary: Decimal,
    include_without_salary: bool,
    is_remote: bool,
    posted_on: datetime,
    location_code: str | None = None,
):
    filters: list[sa.UnaryExpression] = [
        Job.is_active.is_(True),
        Job.posted_on >= posted_on,
    ]
    if is_remote is not None:  # allow filtering for both remote and non-remote jobs
        filters.append(Job.is_remote == is_remote)

    if include_without_salary:
        filters.append(
            sa.or_(
                Job.max_salary >= min_salary,
                Job.min_salary >= min_salary,
                sa.and_(
                    Job.max_salary.is_(None),
                    Job.min_salary.is_(None),
                ),
            )
        )
    else:
        filters.append(
            sa.or_(
                Job.max_salary >= min_salary,
                # this is for the case where max_salary is None
                Job.min_salary >= min_salary,
            )
        )

    if tags:
        tag_conditions = [sa.func.lower(Tag.name) == sa.func.lower(tag) for tag in tags]
        filters.append(sa.or_(*tag_conditions))

    if location_code:
        search_codes = [location_code] + SUBDIVISION_MAP.get(location_code, [])
        filters.append(
            sa.or_(
                Job.locations.is_(None),
                Job.locations == [],
                Job.locations.op("&&")(search_codes),
            )
        )

    return filters
