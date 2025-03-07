from datetime import datetime, timezone, timedelta
from decimal import Decimal

import markdown

from job_notifier.models import Job


def test_job_without_posted_on():
    job = Job(
        title="Python Developer",
        salary=Decimal(str(80_000)),
        link="https://example.com",
    )
    assert (
        str(job).strip()
        == markdown.markdown("""
        ### Title: Python Developer
        **Salary: $80,000**
        Link: https://example.com
        Posted: None
    """).strip()
    )


def test_job_with_posted_on_in_datetime():
    job = Job(
        title="Python Developer",
        salary=Decimal(str(80_000)),
        link="https://example.com",
        posted_on=datetime.now(timezone.utc) - timedelta(days=5),
    )
    assert (
        str(job).strip()
        == markdown.markdown("""
        ### Title: Python Developer
        **Salary: $80,000**
        Link: https://example.com
        Posted: 5 days ago
    """).strip()
    )

    # with difference in hours
    job = Job(
        title="Python Developer",
        salary=Decimal(str(80_000)),
        link="https://example.com",
        posted_on=datetime.now(timezone.utc) - timedelta(hours=5),
    )
    assert (
        str(job).strip()
        == markdown.markdown("""
        ### Title: Python Developer
        **Salary: $80,000**
        Link: https://example.com
        Posted: 5 hours ago
    """).strip()
    )


def test_job_without_posted_in_str():
    job = Job(
        title="Python Developer",
        salary=Decimal(str(80_000)),
        link="https://example.com",
        posted_on="5 days ago",
    )
    assert (
        str(job).strip()
        == markdown.markdown("""
        ### Title: Python Developer
        **Salary: $80,000**
        Link: https://example.com
        Posted: 5 days ago
    """).strip()
    )
