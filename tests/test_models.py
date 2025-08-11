from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal
from unittest import mock

import pytest
import sqlalchemy as sa
from sqlalchemy import func

from job_board import config
from job_board.connection import get_session
from job_board.models import Job
from job_board.models import Payload
from job_board.models import purge_old_jobs
from job_board.models import store_jobs
from job_board.models import Tag
from job_board.portals.models import Portal
from job_board.portals.parser import Job as JobListing


now = datetime.now(timezone.utc)


def test_session_can_be_used_only_during_tests(db_session):
    with mock.patch.object(config, "ENV", "prod"):
        with pytest.raises(RuntimeError):
            with get_session():
                pass  # pragma: no cover


def test_read_only_session(db_setup):
    with get_session(readonly=True) as session:
        with pytest.raises(sa.exc.InternalError) as exc:
            session.execute(
                sa.insert(Job).values(
                    link="http://example.com",
                    title="Test Job",
                    posted_on=now,
                )
            )

    assert "cannot execute INSERT in a read-only transaction" in str(exc.value)


def test_portal_get_or_create_with_invalid_portal_name():
    with pytest.raises(ValueError) as exception:
        Portal.get_or_create(name="invalid_portal")

    assert "invalid_portal" in str(exception)


def test_portal_fetch_with_invalid_portal_name():
    with pytest.raises(ValueError) as exception:
        Portal.fetch_jobs(name="invalid-portal")

    assert "invalid-portal" in str(exception)


def test_store_jobs(db_session):
    # No job_listings, nothing happens
    assert store_jobs([]) is None

    job_listings = [
        JobListing(
            link="https://remotive.com/jobs/job1",
            title="Job 1",
            salary=Decimal(str(80_000)),
            posted_on=now - timedelta(days=1),
            tags=["python", "remote"],
            is_remote=True,
            locations=["US", "IN"],
            description="Looking for Django and FastAPI developer",
            payload="some data",
            company_name="Test Company",
        ),
        JobListing(
            link="https://wellfound.com/jobs/job2",
            title="Job 2",
            salary=Decimal(str(100_000)),
            tags=["python", "django"],
            is_remote=False,
            payload="some data",
            company_name="Test Company",
        ),
        JobListing(
            link="https://himalayas.app/jobs/job3",
            title="Job 3",
            salary=Decimal(str(100_000)),
            is_remote=False,
            payload="some data",
            company_name="Test Company",
        ),
    ]

    store_jobs(job_listings)

    jobs = db_session.execute(sa.select(Job)).scalars().all()

    assert {j.link for j in jobs} == {
        "https://remotive.com/jobs/job1",
        "https://wellfound.com/jobs/job2",
        "https://himalayas.app/jobs/job3",
    }

    # Test portal_name property
    assert {j.portal_name for j in jobs} == {"Remotive", "Wellfound", "Himalayas"}
    assert {t.name for j in jobs for t in j.tags} == {
        "python",
        "remote",
        "django",
    }

    tags = db_session.execute(sa.select(Tag)).scalars().all()
    assert {t.name for t in tags} == {"python", "remote", "django"}

    assert (
        db_session.execute(
            sa.select(sa.func.count())
            .select_from(Payload)
            .where(Payload.link.in_(j.link for j in job_listings))
        ).scalar_one()
        == 3
    )
    assert (
        db_session.execute(
            sa.select(sa.func.count()).where(Job.portal_name == "Remotive")
        ).scalar_one()
        == 1
    )

    # Check that the method is idempotent
    store_jobs(job_listings)
    assert (
        db_session.execute(sa.select(sa.func.count()).select_from(Job)).scalar_one()
        == 3
    )
    assert (
        db_session.execute(sa.select(sa.func.count()).select_from(Payload)).scalar_one()
        == 3
    )


def test_store_jobs_with_empty_tags(db_session):
    job_listings = [
        JobListing(
            link="https://job1.com",
            title="Job 1",
            posted_on=now - timedelta(days=1),
            payload="some data",
            company_name="Test Company",
        ),
    ]

    store_jobs(job_listings)

    jobs = db_session.execute(sa.select(Job)).scalars().all()

    assert {j.link for j in jobs} == {"https://job1.com"}
    assert len(jobs[0].tags) == 0

    tags = db_session.execute(sa.select(Tag)).scalars().all()
    assert len(tags) == 0


def test_purge_old_jobs(db_session):
    job_listings = [
        JobListing(
            link="https://example.com/new-job",
            title="Job 1",
            posted_on=now - timedelta(days=1),
            payload="some data",
            company_name="New Company",
        ),
        JobListing(
            link="https://example.com/old-job",
            title="Job 2",
            posted_on=now - timedelta(days=365),
            payload="some data",
            company_name="Old Company",
        ),
    ]

    store_jobs(job_listings)

    assert (db_session.execute(sa.select(func.count(Job.id))).scalars().one()) == 2
    assert (db_session.execute(sa.select(func.count(Payload.id))).scalars().one()) == 2

    purge_old_jobs()

    assert "new-job" in db_session.execute(sa.select((Job.link))).scalars().one()
    assert "new-job" in db_session.execute(sa.select(Payload.link)).scalars().one()


def test_fill_missing_tags(db_session):
    job = Job(
        title="job-title",
        description="job-description",
        link="https://example.com/2",
        company_name="Test Company",
    )
    db_session.add(job)

    with mock.patch(
        "job_board.models.extract_job_tags_using_llm",
        return_value=[
            JobListing(
                title=job.title,
                link=job.link,
                tags=["new", "tag"],
                company_name=job.company_name,
            )
        ],
    ):
        Job.fill_missing_tags()

    db_session.refresh(job)
    assert {t.name for t in job.tags} == {"new", "tag"}

    # call the method again to ensure its idempotent.
    Job.fill_missing_tags()


def test_location_check_constraint(db_session):
    valid_job = Job(
        title="Valid Location Job",
        link="https://example.com/valid",
        locations=["US", "IN", "US-CA"],
        posted_on=now,
        company_name="Valid Company",
    )
    db_session.add(valid_job)
    db_session.commit()

    invalid_job = Job(
        title="Invalid Location Job",
        link="https://example.com/invalid",
        locations=["INVALID", "New York"],
        posted_on=now,
        company_name="Invalid Company",
    )
    with pytest.raises(sa.exc.IntegrityError):
        db_session.add(invalid_job)
        db_session.commit()
