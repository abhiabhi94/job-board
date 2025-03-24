from datetime import datetime, timedelta, timezone
from decimal import Decimal


from job_board.base import Job


def test_job_str():
    now = datetime.now(timezone.utc)

    job = Job(
        link="https://python.org/jobs/1/",
        title="Software Engineer",
        salary=Decimal(str(120_000.75)),
        posted_on=now - timedelta(days=3, hours=5),
        notified=False,
    )

    expected_output = """\
Title      : Software Engineer
Salary     : 120,000.75
Link       : https://python.org/jobs/1/
Posted On  : 3 days ago\
"""
    assert str(job) == expected_output

    job = Job(
        link="https://python.org/jobs/1/",
        title="Software Engineer",
        salary=Decimal(str(120_000.75)),
        posted_on=None,
    )

    expected_output = """\
Title      : Software Engineer
Salary     : 120,000.75
Link       : https://python.org/jobs/1/
Posted On  : N/A\
"""
    assert str(job) == expected_output
