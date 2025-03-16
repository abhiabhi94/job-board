from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest import mock


from job_board.models import Job
from job_board.base import JobListing

import pytest
import sqlalchemy
from job_board.models import (
    Base as BaseModel,
    store_jobs,
    notify,
    create_tables,
)
from job_board.connection import engine, Session


@pytest.fixture(scope="session")
def db_setup():
    create_tables()
    yield
    BaseModel.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_setup):
    """
    Returns a sqlalchemy session, and after the test, it tears down everything properly.
    """
    connection = engine.connect()
    # begin the nested transaction
    transaction = connection.begin()
    # use the connection with the already started transaction
    session = Session(bind=connection)

    with mock.patch("job_board.connection.Session.begin") as mock_begin:
        # Ensure `Session.begin()` always returns `db_session`
        mock_begin.return_value.__enter__.return_value = session
        yield session

    session.close()
    # roll back the broader transaction
    transaction.rollback()
    # put back the connection to the connection pool
    connection.close()


now = datetime.now(timezone.utc)


def test_store_jobs(db_session):
    # No job_listings, nothing happens
    assert store_jobs([]) is None

    job_listings = [
        JobListing(
            link="http://job1.com",
            title="Job 1",
            salary=Decimal(str(80_000)),
            posted_on=now - timedelta(days=1),
        ),
        JobListing(
            link="http://job2.com",
            title="Job 2",
            salary=Decimal(str(100_000)),
            posted_on=now - timedelta(days=2),
        ),
    ]

    store_jobs(job_listings)

    jobs = db_session.execute(sqlalchemy.select(Job)).scalars().all()

    assert {j.link for j in jobs} == {
        "http://job1.com",
        "http://job2.com",
    }


def test_notify(db_session):
    # No jobs to notify, nothing happens
    notify()

    job = Job(
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
