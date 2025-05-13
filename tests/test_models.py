from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal
from unittest import mock

import pytest
import sqlalchemy

from job_board import config
from job_board.base import Job
from job_board.connection import get_session
from job_board.models import Job as JobModel
from job_board.models import store_jobs
from job_board.models import Tag
from job_board.portals.models import PortalSetting


now = datetime.now(timezone.utc)


def test_session_can_be_used_only_during_tests(db_session):
    with mock.patch.object(config, "TEST_ENV", False):
        with pytest.raises(RuntimeError):
            with get_session():
                pass


def test_read_only_session(db_setup):
    with get_session(readonly=True) as session:
        with pytest.raises(sqlalchemy.exc.InternalError) as exc:
            session.execute(
                sqlalchemy.insert(JobModel).values(
                    link="http://example.com",
                    title="Test Job",
                    salary=Decimal(str(100_000)),
                    posted_on=now,
                )
            )

    assert "cannot execute INSERT in a read-only transaction" in str(exc.value)


def test_portal_setting_get_or_create_with_invalid_portal_name():
    with pytest.raises(ValueError) as exception:
        PortalSetting.get_or_create(portal_name="invalid_portal")

    assert "invalid_portal" in str(exception)


def test_store_jobs(db_session):
    # No job_listings, nothing happens
    assert store_jobs([]) is None

    job_listings = [
        Job(
            link="http://job1.com",
            title="Job 1",
            salary=Decimal(str(80_000)),
            posted_on=now - timedelta(days=1),
            tags=["python", "remote"],
            is_remote=True,
            locations=["New York", "Remote"],
            description="Looking for Django and FastAPI developer",
        ),
        Job(
            link="http://job2.com",
            title="Job 2",
            salary=Decimal(str(100_000)),
            tags=["python", "django"],
            is_remote=False,
        ),
        Job(
            link="http://job3.com",
            title="Job 3",
            salary=Decimal(str(100_000)),
            is_remote=False,
        ),
    ]

    store_jobs(job_listings)

    jobs = db_session.execute(sqlalchemy.select(JobModel)).scalars().all()

    assert {j.link for j in jobs} == {
        "http://job1.com",
        "http://job2.com",
        "http://job3.com",
    }
    assert {t.name for j in jobs for t in j.tags} == {
        "python",
        "remote",
        "django",
    }

    tags = db_session.execute(sqlalchemy.select(Tag)).scalars().all()
    assert {t.name for t in tags} == {"python", "remote", "django"}

    # Check that the method is idempotent
    store_jobs(job_listings)
    assert (
        db_session.execute(
            sqlalchemy.select(sqlalchemy.func.count()).select_from(JobModel)
        ).scalar_one()
        == 3
    )
