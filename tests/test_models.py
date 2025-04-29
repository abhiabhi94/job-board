from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest import mock

from job_board.models import Job as JobModel
from job_board.base import Job
from job_board import config

import sqlalchemy
import pytest

from job_board.models import (
    store_jobs,
    notify,
)
from job_board.connection import get_session
from job_board.portals.models import PortalSetting


now = datetime.now(timezone.utc)


def test_session_can_be_used_only_during_tests(db_session):
    with mock.patch.object(config, "TEST_ENV", False):
        with pytest.raises(RuntimeError):
            get_session()


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
        ),
        Job(
            link="http://job2.com",
            title="Job 2",
            salary=Decimal(str(100_000)),
        ),
    ]

    store_jobs(job_listings)

    jobs = db_session.execute(sqlalchemy.select(JobModel)).scalars().all()

    assert {j.link for j in jobs} == {
        "http://job1.com",
        "http://job2.com",
    }


def test_notify(db_session):
    # No jobs to notify, nothing happens
    notify()
    job_1 = JobModel(
        link="http://job-1.com",
        title="Job Title",
        salary=Decimal(str(70_000)),
        posted_on=now - timedelta(days=1),
    )
    job_2 = JobModel(
        link="http://job-2.com",
        title="Job Title",
        salary=Decimal(str(80_000)),
        posted_on=now - timedelta(days=1),
    )
    db_session.add_all([job_1, job_2])

    with (
        mock.patch(
            "job_board.notifier.mail.EmailProvider.create_service"
        ) as mock_service,
        mock.patch(
            "job_board.notifier.mail.EmailProvider.send_email"
        ) as mock_send_email,
        mock.patch.object(config, "MAX_JOBS_PER_EMAIL", 1),
    ):
        notify()

    mock_service.assert_called_once()
    assert mock_send_email.call_count == 2

    # Check that the jobs are marked as notified
    ids = [job_1.id, job_2.id]
    statement = (
        sqlalchemy.select(sqlalchemy.func.count())
        .select_from(JobModel)
        .where(JobModel.id.in_(ids), JobModel.notified.is_(True))
    )
    count = db_session.execute(statement).scalar_one()

    assert count == len(ids)
