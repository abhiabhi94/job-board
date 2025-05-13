from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal

from job_board.base import Job


def test_job_str():
    now = datetime.now(timezone.utc)

    job = Job(
        link="https://python.org/jobs/1/",
        title="Software Engineer",
        salary=Decimal(str(120_000.75)),
        posted_on=now - timedelta(days=3, hours=5),
        description=None,
        tags=["python"],
        is_remote=True,
        locations=["New York", "Remote"],
    )

    expected_output = """\
Title        : Software Engineer
Description  : N/A
Link         : https://python.org/jobs/1/
Salary       : 120,000.75
Posted On    : 3 days ago
Tags         : python
Is Remote    : Yes
Locations    : New York, Remote\
"""
    assert str(job) == expected_output
