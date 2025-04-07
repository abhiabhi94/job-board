from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest import mock

from job_board.models import Job as JobModel
from job_board.base import Job

import sqlalchemy
from job_board.models import (
    store_jobs,
    notify,
)


now = datetime.now(timezone.utc)


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

    job = JobModel(
        link="http://job.com",
        title="Job Title",
        salary=Decimal(str(70_000)),
        posted_on=now - timedelta(days=1),
    )
    db_session.add(job)
    db_session.commit()

    with (
        mock.patch(
            "job_board.notifier.mail.EmailProvider.create_service"
        ) as mock_service,
        mock.patch(
            "job_board.notifier.mail.EmailProvider.send_email"
        ) as mock_send_email,
    ):
        notify()

    db_session.refresh(job)
    assert job.notified is True
    mock_service.assert_called_once()
    mock_send_email.assert_called_once()
