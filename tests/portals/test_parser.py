import json
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal
from unittest.mock import patch

import httpx
import pytest
from lxml import html

from job_board.portals.base import BasePortal
from job_board.portals.parser import extract_job_tags_using_llm
from job_board.portals.parser import InvalidSalary
from job_board.portals.parser import Job
from job_board.portals.parser import JobParser
from job_board.portals.parser import OPENAI_RESPONSES_API_URL

now = datetime.now(timezone.utc)


@pytest.fixture
def parser():
    return JobParser(api_data_format="json", item={})


@pytest.mark.parametrize(
    ("method_name"),
    [
        "get_tags",
        "get_link",
        "get_title",
        "get_description",
        "get_posted_on",
        "get_salary_range",
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
def test_parse_salary_info(parser, test_case):
    parser.get_link = lambda: "https://example.com"
    amount_currency = parser.parse_salary(test_case["salary_value"])

    assert amount_currency.amount == test_case["expected_result"]


@pytest.mark.parametrize(
    ("salary", "expected_error"),
    [
        ("", "no salary info"),
        ("negotiable", "unsupported salary format"),
    ],
)
def test_parse_salary_info_invalid(parser, salary, expected_error):
    parser.get_link = lambda: "https://example.com"
    with pytest.raises(InvalidSalary, match=expected_error):
        parser.extract_salary(salary)


@pytest.mark.parametrize(
    (
        "compensation",
        "expected_currency",
        "expected_min_salary",
        "expected_max_salary",
    ),
    [
        # Format: "<min_salary> – <max_salary> • <equity info>"
        ("$100k – $150k • details", "USD", 100_000, 150_000),
        ("$100k – $150k CAD • details", "CAD", 100_000, 150_000),
        ("$100k – $150k • 1.0% – 2.0%", "USD", 100_000, 150_000),
        ("$100m – $150m • details", "USD", 100_000_000, 150_000_000),
        ("$100b – $150b • details", "USD", 100_000_000_000, 150_000_000_000),
        ("90000 – 120000", "USD", 90_000, 120_000),
        ("$2.5K – $3K", "USD", 2500, 3000),
        (
            "₹15L – ₹25L • details",
            "INR",
            1_500_000,
            2_500_000,
        ),
    ],
)
def test_get_currency_and_salary_range_valid(
    parser,
    compensation,
    expected_currency,
    expected_min_salary,
    expected_max_salary,
):
    parser.get_link = lambda: "https://example.com"
    parser.get_posted_on = lambda: now.date()

    salary_range = parser.extract_salary_range(compensation=compensation)
    min_salary = salary_range.min_salary
    max_salary = salary_range.max_salary

    assert min_salary.currency == expected_currency == max_salary.currency
    assert min_salary.amount == Decimal(str(expected_min_salary))
    assert max_salary.amount == Decimal(str(expected_max_salary))


@pytest.mark.parametrize(
    (
        "compensation",
        "error_message",
    ),
    [
        ("₨35k – ₨60k", "unsupported .* currency_symbol='₨'"),
        ("negotiable", "unsupported salary format"),
    ],
)
def test_get_currency_and_salary_range_invalid(parser, compensation, error_message):
    parser.get_link = lambda: "https://example.com"
    parser.get_posted_on = lambda: now.date()

    with pytest.raises(InvalidSalary, match=error_message):
        parser.extract_salary_range(compensation=compensation)


def test_get_payload_for_unsupported_format(parser):
    parser.api_data_format = "something"
    with pytest.raises(ValueError, match="Unsupported data format: something"):
        parser.get_payload()


def test_very_old_jobs_are_skipped(db_session):
    class TestParser(JobParser):
        def get_link(self):
            return self.item["link"]

        def get_posted_on(self):
            return self.item["posted_on"]

        def get_job(self):
            return self.item

    portal = BasePortal()
    portal.parser_class = TestParser
    portal.api_data_format = "json"

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
        (fetched_job,) = portal.fetch_jobs()

    assert fetched_job["link"] == recent_job["link"]


@pytest.mark.parametrize(
    "min_salary,max_salary,expected_output",
    [
        # Both min and max salary are present and equal
        (Decimal("100000"), Decimal("100000"), "$100K"),
        # Both min and max salary are present and different
        (Decimal("80000"), Decimal("120000"), "$80K - $120K"),
        # Only min salary is present
        (Decimal("75000"), None, "$75K and above"),
        # Only max salary is present
        (None, Decimal("150000"), "Up to $150K"),
        # Neither min nor max salary is present
        (None, None, ""),
        # Large amounts with proper formatting
        (Decimal("1000000"), Decimal("2000000"), "$1M - $2M"),
        # Small amounts
        (Decimal("50000"), Decimal("60000"), "$50K - $60K"),
        # Decimal amounts that round to same value
        (Decimal("99999.99"), Decimal("100000.01"), "$100K"),
    ],
)
def test_salary_range_property(min_salary, max_salary, expected_output):
    job = Job(
        title="Test Job",
        link="https://example.com/job",
        min_salary=min_salary,
        max_salary=max_salary,
    )

    assert job.salary_range == expected_output


def test_extract_job_tags_using_llm(respx_mock, load_response):
    assert extract_job_tags_using_llm([]) == []
    jobs = [
        Job(
            title="All Round DevOps Engineer",
            description="description 1",
            link="https://wellfound.com/jobs/3326702-all-round-devops-engineer",
        ),
        Job(
            title="AI/ML Engineer",
            description="description 2",
            link="https://wellfound.com/jobs/3326697-ai-ml-engineer",
        ),
        Job(
            title="Security Engineer",
            description="description 3",
            link="https://wellfound.com/jobs/3326692-security-engineer",
        ),
        Job(
            title="Senior Autonomy Engineer II - Simulation",
            description="description 4",
            link="https://wellfound.com/jobs/3326689-senior-autonomy-engineer-ii-simulation",
        ),
        Job(
            title="Senior Director, Business Systems Engineering, Employee Tech Group",
            description="description 5",
            link="https://wellfound.com/jobs/3326626-senior-director-business-systems-engineering-employee-tech-group",
        ),
    ]

    respx_mock.post(OPENAI_RESPONSES_API_URL).mock(
        return_value=httpx.Response(
            status_code=200,
            text=load_response("openai.json"),
        )
    )

    tags_response = extract_job_tags_using_llm(jobs)

    assert tags_response == [
        Job(
            title="All Round DevOps Engineer",
            description="description 1",
            link="https://wellfound.com/jobs/3326702-all-round-devops-engineer",
            tags=["azure", "c#", ".net", "pyspark", "sql"],
        ),
        Job(
            title="AI/ML Engineer",
            description="description 2",
            link="https://wellfound.com/jobs/3326697-ai-ml-engineer",
            tags=["python", "tensorflow", "pytorch", "computer vision", "flask"],
        ),
        Job(
            title="Security Engineer",
            description="description 3",
            link="https://wellfound.com/jobs/3326692-security-engineer",
            tags=["aws", "linux", "python", "soar", "edr/xdr"],
        ),
        Job(
            title="Senior Autonomy Engineer II - Simulation",
            description="description 4",
            link="https://wellfound.com/jobs/3326689-senior-autonomy-engineer-ii-simulation",
            tags=["c++", "python", "simulation", "linux", "data structures"],
        ),
        Job(
            title="Senior Director, Business Systems Engineering, Employee Tech Group",
            description="description 5",
            link="https://wellfound.com/jobs/3326626-senior-director-business-systems-engineering-employee-tech-group",
            tags=["servicenow", "workday", "workato", "ai/ml", "systems engineering"],
        ),
    ]


@pytest.mark.parametrize(
    "data, iso_codes",
    [
        (
            {
                "applicantLocationRequirements": [
                    {"name": "United States"},
                    {"name": "Canada"},
                    {"name": "Remote"},
                ]
            },
            ["US", "CA"],
        ),
        (
            {"applicantLocationRequirements": {"name": "United Kingdom"}},
            ["GB"],
        ),
        ({"applicantLocationRequirements": []}, []),
        ({}, []),
    ],
)
def test_parse_locations_from_json_ld(data, iso_codes, parser):
    document = html.fromstring(
        f'<script type="application/ld+json">{json.dumps(data)}</script>'
    )
    locations = parser.parse_locations_from_json_ld(document)
    assert locations == iso_codes
