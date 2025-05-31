from datetime import datetime
from datetime import timedelta
from datetime import timezone

from job_board.query import count_jobs
from job_board.query import filter_jobs

now = datetime.now(timezone.utc)


def test_count_jobs(db_session):
    assert (
        count_jobs(
            tags=["python", "remote"],
            min_salary=20000,
            include_no_salary=False,
            posted_on=now - timedelta(days=30),
            is_remote=True,
        )
        == 0
    )


def test_filter_jobs(db_session):
    assert (
        filter_jobs(
            tags=[],
            min_salary=0,
            include_no_salary=False,
            is_remote=True,
            posted_on=now - timedelta(days=30),
            order_by=None,
            offset=0,
            limit=10,
        )
        == []
    )
