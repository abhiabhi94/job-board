from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal
from unittest.mock import patch

import pytest

from job_board.portals.base import BasePortal
from job_board.portals.parser import Job
from job_board.portals.parser import JobParser


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
        payload="some data",
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


now = datetime.now(timezone.utc)


@pytest.fixture
def parser():
    return JobParser(portal_name="test_portal", api_data_format="json", item={})


@pytest.mark.parametrize(
    ("method_name"),
    [
        "get_tags",
        "get_link",
        "get_title",
        "get_description",
        "get_posted_on",
        "get_salary",
        "get_is_remote",
        "get_extra_info",
    ],
)
def test_abstract_methods(method_name, parser):
    with pytest.raises(NotImplementedError):
        getattr(parser, method_name)()


@pytest.mark.parametrize(
    "test_case",
    [
        # Valid salary
        pytest.param(
            {
                "salary_value": "100000",
                "expected_result": Decimal("100000"),
            },
            id="valid_salary_above_minimum",
        ),
        # Valid salary with currency symbol and commas
        pytest.param(
            {
                "salary_value": "$120,000",
                "min_salary": Decimal("100000"),
                "expected_result": Decimal("120000"),
            },
            id="valid_salary_with_formatting",
        ),
        # Invalid salary format
        pytest.param(
            {
                "salary_value": "negotiable",
                "expected_result": None,
            },
            id="invalid_salary_format",
        ),
        # None salary
        pytest.param(
            {
                "salary_value": None,
                "expected_result": None,
            },
            id="no_salary",
        ),
    ],
)
def test_parse_salary(parser, test_case):
    parser.get_link = lambda: "https://example.com"
    result = parser.parse_salary(salary_str=test_case["salary_value"])

    assert result == test_case["expected_result"]


@pytest.mark.parametrize(
    ("compensation", "expected_currency", "expected_salary"),
    [
        # Format: "<ignored part> – <salary_info> • <equity info>"
        ("$100k – $150k • details", "USD", 150_000),
        ("$100k – $150k CAD • details", "CAD", 150_000),
        ("$100k – $150k • 1.0% – 2.0%", "USD", 150_000),
        ("$100m – $150m • details", "USD", 150_000_000),
        ("$100b – $150b • details", "USD", 150_000_000_000),
        ("90000 – 120000", "USD", 120_000),
        (
            "₹15L – ₹25L • details",
            "INR",
            2_500_000,
        ),
    ],
)
def test_get_currency_and_salary(
    parser, compensation, expected_currency, expected_salary
):
    parser.get_link = lambda: "https://example.com"

    currency, salary = parser.get_currency_and_salary(
        compensation=compensation, range_separator="–"
    )

    assert currency == expected_currency
    assert salary == expected_salary


def test_get_payload_for_unsupported_format(parser):
    parser.api_data_format = "something"
    with pytest.raises(ValueError, match="Unsupported data format: something"):
        parser.get_payload()


def test_very_old_jobs_are_skipped(parser):
    class TestParser(JobParser):
        def get_link(self):
            return self.item["link"]

        def get_posted_on(self):
            return self.item["posted_on"]

        def _get_job(self):
            return self.item

    portal = BasePortal()
    portal.parser_class = TestParser
    portal.api_data_format = "json"
    portal.portal_name = "test_portal"

    outdated_job = {
        "link": "https://example.com/job/1",
        "posted_on": now - timedelta(days=366),
    }
    recent_job = {
        "link": "https://example.com/job/2",
        "posted_on": now - timedelta(days=3),
    }
    jobs = [outdated_job, recent_job]
    with (
        patch.object(portal, "make_request"),
        patch.object(portal, "get_items", return_value=jobs),
    ):
        (fetched_job,) = portal.get_jobs()

    assert fetched_job["link"] == recent_job["link"]
