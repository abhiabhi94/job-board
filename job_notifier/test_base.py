from datetime import datetime, timezone, timedelta
from decimal import Decimal

import markdown

from job_notifier.base import Message


def test_message_without_posted_on():
    message = Message(
        title="Python Developer",
        salary=Decimal(str(80_000)),
        link="https://example.com",
    )
    assert (
        str(message).strip()
        == markdown.markdown("""
        ### Title: Python Developer
        **Salary: $80,000**
        Link: https://example.com
        Posted: None
    """).strip()
    )


def test_message_with_posted_on_in_datetime():
    message = Message(
        title="Python Developer",
        salary=Decimal(str(80_000)),
        link="https://example.com",
        posted_on=datetime.now(timezone.utc) - timedelta(days=5),
    )
    assert (
        str(message).strip()
        == markdown.markdown("""
        ### Title: Python Developer
        **Salary: $80,000**
        Link: https://example.com
        Posted: 5 days ago
    """).strip()
    )

    # with difference in hours
    message = Message(
        title="Python Developer",
        salary=Decimal(str(80_000)),
        link="https://example.com",
        posted_on=datetime.now(timezone.utc) - timedelta(hours=5),
    )
    assert (
        str(message).strip()
        == markdown.markdown("""
        ### Title: Python Developer
        **Salary: $80,000**
        Link: https://example.com
        Posted: 5 hours ago
    """).strip()
    )


def test_message_without_posted_in_str():
    message = Message(
        title="Python Developer",
        salary=Decimal(str(80_000)),
        link="https://example.com",
        posted_on="5 days ago",
    )
    assert (
        str(message).strip()
        == markdown.markdown("""
        ### Title: Python Developer
        **Salary: $80,000**
        Link: https://example.com
        Posted: 5 days ago
    """).strip()
    )
