from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import json

import pytest

from job_board import config
from job_board.base import Job
from job_board.portals.wellfound import Wellfound


@pytest.fixture
def wellfound():
    """Fixture to create a Wellfound instance with mock methods."""
    portal = Wellfound()
    return portal


def create_job_result(override_data=None):
    job_data = {
        "slug": "test-job",
        "id": "123",
        "remote": True,
        "liveStartAt": datetime.now(tz=timezone.utc).timestamp(),
        "title": "Python Developer",
        "description": "Job description",
        "compensation": "$200K – $300K • details",
    }
    job_data.update(override_data or {})
    return job_data


@pytest.mark.parametrize(
    ("compensation", "expected_currency", "expected_salary"),
    [
        # Format: "<ignored part> – <salary_info> • <equity info>"
        ("$100k – $150k • details", "USD", Decimal("150") * 1_000),
        ("$100k – $150k • 1.0% – 2.0%", "USD", Decimal("150") * 1_000),
        ("$100m – $150m • details", "USD", Decimal("150") * 1_000_000),
        ("$100b – $150b • details", "USD", Decimal("150") * 1_000_000_000),
        (
            "₹15L – ₹25L • details",
            "INR",
            Decimal("25") * 100_000,
        ),
    ],
)
def test_get_currency_and_salary(
    wellfound, compensation, expected_currency, expected_salary
):
    link = "https://example.com"

    currency, salary = wellfound.get_currency_and_salary(link, compensation)

    assert currency.name == expected_currency
    assert salary == expected_salary


@pytest.mark.parametrize(
    ("job_data", "config_salary"),
    [
        # non-remote job
        ({"remote": False}, Decimal("100_000")),
        # without compensation
        ({"compensation": ""}, Decimal("100_000")),
        # below salary threshold
        ({"compensation": "$100k – $150k • details"}, Decimal("200_000")),
        # invalid salary i.e doesn't match the expected salary format.
        ({"compensation": "₹10,000 – ₹15,000"}, Decimal("200_000")),
        # no salary info
        ({"compensation": "No Equity"}, Decimal("200_000")),
        # too old job
        (
            {
                "liveStartAt": (
                    datetime.now(tz=timezone.utc) - timedelta(days=365)
                ).timestamp(),
            },
            Decimal("200_000"),
        ),
        # non-matching keywords
        (
            {
                "title": "Typescript Developer",
                "description": "Job description",
            },
            Decimal("200_000"),
        ),
    ],
)
def test_filter_job_invalid(wellfound, job_data, config_salary):
    job_result = create_job_result(job_data)

    with patch.object(config, "SALARY", config_salary):
        job = wellfound.filter_job(job_result)

    assert job is None


def test_filter_jobs_valid(wellfound):
    valid_job = create_job_result()
    response_data = json.dumps(
        {
            "props": {
                "pageProps": {
                    "apolloState": {
                        "data": {
                            "JobListingSearchResult:123": valid_job,
                            "JobListingSearchResult:456": create_job_result(
                                {"remote": False}
                            ),
                        },
                    },
                },
            }
        }
    )

    with patch.object(wellfound.scrapfly_client, "scrape") as mock_scrape:
        mock_scrape.return_value = MagicMock(autospec=True)
        mock_scrape.return_value.scrape_result = {
            "content": f"""
            <html>
                <body>
                    <div id="__NEXT_DATA__">
                        {response_data}
                    </div>
                </body>
            </html>
            """
        }

        (job,) = wellfound.get_jobs()

    assert isinstance(job, Job)
    assert valid_job["slug"] in job.link
    assert valid_job["id"] in job.link
    assert job.title == valid_job["title"]
