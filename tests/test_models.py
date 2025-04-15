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
    notify([])
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
    db_session.commit()

    from job_board import config

    with (
        mock.patch(
            "job_board.notifier.mail.EmailProvider.create_service"
        ) as mock_service,
        mock.patch(
            "job_board.notifier.mail.EmailProvider.send_email"
        ) as mock_send_email,
        mock.patch.object(config, "MAX_JOBS_PER_EMAIL", 1),
    ):
        notify([job_1.id, job_2.id])

    mock_service.assert_called_once()
    assert mock_send_email.call_count == 2

    db_session.refresh(job_1)
    assert job_1.notified is True
    db_session.refresh(job_2)
    assert job_2.notified is True

    # calling notify again should not send email
    # so nothing is patched.
    notify([job_1.id, job_2.id])
