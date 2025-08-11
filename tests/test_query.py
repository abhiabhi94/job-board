from datetime import datetime
from datetime import timedelta
from datetime import timezone

from job_board.models import store_jobs
from job_board.portals.parser import Job as JobListing
from job_board.query import count_jobs
from job_board.query import filter_jobs

now = datetime.now(timezone.utc)


def test_count_jobs(db_session):
    store_jobs([])
    assert (
        count_jobs(
            tags=["python", "remote"],
            min_salary=20000,
            include_without_salary=False,
            posted_on=now - timedelta(days=30),
            is_remote=True,
        )
        == 0
    )

    store_jobs(
        [
            JobListing(
                link="https://example.com/job1",
                title="Job 1",
                min_salary=30000,
                is_remote=True,
                posted_on=now - timedelta(days=10),
                tags=["python", "remote"],
                payload="some data",
                company_name="Test Company",
            ),
            JobListing(
                link="https://example.com/job2",
                title="Job 2",
                min_salary=25000,
                is_remote=True,
                posted_on=now - timedelta(days=20),
                tags=["python"],
                payload="some data",
                company_name="Test Company",
            ),
            JobListing(
                link="https://example.com/job3",
                title="Job 3",
                min_salary=None,
                is_remote=False,
                posted_on=now - timedelta(days=5),
                tags=["developer"],
                payload="some data",
                company_name="Test Company",
            ),
        ]
    )

    # non-remote jobs
    assert (
        count_jobs(
            tags=[],
            min_salary=20000,
            include_without_salary=True,
            posted_on=now - timedelta(days=30),
            is_remote=False,
        )
        == 1
    )

    # all remote jobs with salary
    assert (
        count_jobs(
            tags=["python", "remote"],
            min_salary=20000,
            include_without_salary=False,
            posted_on=now - timedelta(days=30),
            is_remote=True,
        )
        == 2
    )

    # tags joined using any
    assert (
        count_jobs(
            tags=["python"],
            min_salary=20000,
            include_without_salary=False,
            posted_on=now - timedelta(days=30),
            is_remote=True,
        )
        == 2
    )

    # all remote/non-remote jobs
    assert (
        count_jobs(
            tags=[],
            min_salary=0,
            include_without_salary=True,
            posted_on=now - timedelta(days=30),
            is_remote=None,
        )
        == 3
    )


def test_filter_jobs(db_session):
    assert (
        filter_jobs(
            tags=[],
            min_salary=0,
            include_without_salary=False,
            is_remote=True,
            posted_on=now - timedelta(days=30),
            order_by=None,
            offset=0,
            limit=10,
        )
        == []
    )

    store_jobs(
        [
            JobListing(
                link="https://example.com/job1",
                title="Job 1",
                min_salary=30000,
                is_remote=True,
                posted_on=now - timedelta(days=10),
                tags=["python", "remote"],
                payload="some data",
                company_name="Test Company",
            ),
            JobListing(
                link="https://example.com/job2",
                title="Job 2",
                min_salary=25000,
                is_remote=True,
                posted_on=now - timedelta(days=20),
                tags=["python"],
                payload="some data",
                company_name="Test Company",
            ),
            JobListing(
                link="https://example.com/job3",
                title="Job 3",
                min_salary=None,
                is_remote=False,
                posted_on=now - timedelta(days=5),
                tags=["developer"],
                payload="some data",
                company_name="Test Company",
            ),
        ]
    )

    jobs = filter_jobs(
        tags=["python", "remote"],
        min_salary=20000,
        include_without_salary=False,
        is_remote=True,
        posted_on=now - timedelta(days=30),
        order_by=None,
        offset=0,
        limit=1,
    )
    assert len(jobs) == 1
    jobs = filter_jobs(
        tags=["python", "remote"],
        min_salary=20000,
        include_without_salary=False,
        is_remote=True,
        posted_on=now - timedelta(days=30),
        order_by=None,
        offset=1,
        limit=1,
    )
    assert len(jobs) == 1
