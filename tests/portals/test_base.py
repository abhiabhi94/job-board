from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal
from unittest.mock import patch

import pytest

from job_board.portals.base import BasePortal

now = datetime.now(timezone.utc)


@pytest.fixture
def portal():
    class Portal(BasePortal):
        portal_name = "placeholder"
        url = "https://example.com/api"
        region_mapping = {"remote": {"worldwide", "remote", "anywhere"}}

    return Portal()


@pytest.mark.parametrize(
    ("method_name"),
    [
        "make_request",
        "get_items",
        "get_link",
        "get_title",
        "get_description",
        "get_posted_on",
        "get_salary",
        "is_remote",
    ],
)
def test_abstract_methods(method_name):
    portal = BasePortal()

    with pytest.raises(NotImplementedError):
        if method_name == "make_request":
            # make_request doesn't require any arguments
            portal.make_request()
        else:
            getattr(portal, method_name)({})


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
def test_parse_salary(portal, test_case):
    portal.get_link = lambda item: "https://example.com"
    result = portal.parse_salary(item={}, salary_str=test_case["salary_value"])

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
    portal, compensation, expected_currency, expected_salary
):
    portal.get_link = lambda item: "https://example.com"

    currency, salary = portal.get_currency_and_salary(
        item={}, compensation=compensation, range_separator="–"
    )

    assert currency == expected_currency
    assert salary == expected_salary


def test_very_old_jobs_are_skipped(portal):
    portal.get_link = lambda item: item["link"]
    portal.get_posted_on = lambda item: item["posted_on"]
    portal.get_job = lambda item: item

    outdated_job = {
        "link": "https://example.com/job/1",
        "title": "Outdated Job",
        "posted_on": now - timedelta(days=366),
        "payload": "some data",
    }
    recent_job = {
        "link": "https://example.com/job/2",
        "title": "Recent Job",
        "posted_on": now - timedelta(days=3),
        "payload": "some data",
    }
    jobs = [outdated_job, recent_job]
    with (
        patch.object(portal, "make_request"),
        patch.object(portal, "get_items", return_value=jobs),
    ):
        (fetched_job,) = portal.get_jobs()

    assert fetched_job["link"] == recent_job["link"]
