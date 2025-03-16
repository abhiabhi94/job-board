import pytest
from decimal import Decimal
from unittest.mock import patch

from job_board.portals.base import BasePortal
from job_board import config


@pytest.fixture
def placeholder_portal():
    class PlaceholderPortal(BasePortal):
        name = "placeholder"
        url = "https://example.com/api"
        region_mapping = {"remote": {"worldwide", "remote", "anywhere"}}

    return PlaceholderPortal()


def test_abstract_methods():
    portal = BasePortal()
    with pytest.raises(NotImplementedError):
        portal.get_jobs_to_notify()


@pytest.mark.parametrize(
    "test_case",
    [
        # matching keyword in title and matching region
        pytest.param(
            {
                "title": "Python Developer",
                "description": "Looking for a developer",
                "region": "worldwide",
                "tags": [],
                "keywords": {"python"},
                "expected_region": "remote",
                "expected_result": True,
            },
            id="matching_keyword_in_title",
        ),
        # matching keyword in description and matching region
        pytest.param(
            {
                "title": "Developer",
                "description": "We need a python expert",
                "region": "worldwide",
                "tags": [],
                "keywords": {"python"},
                "expected_region": "remote",
                "expected_result": True,
            },
            id="matching_keyword_in_description",
        ),
        # matching keyword in tags and matching region
        pytest.param(
            {
                "title": "Developer",
                "description": "We need an expert",
                "region": "worldwide",
                "tags": ["python", "django"],
                "keywords": {"python"},
                "expected_region": "remote",
                "expected_result": True,
            },
            id="matching_keyword_in_tags",
        ),
        # no matching keywords
        pytest.param(
            {
                "title": "Java Developer",
                "description": "Looking for a Java expert",
                "region": "worldwide",
                "tags": ["java", "spring"],
                "keywords": {"python", "django"},
                "expected_region": "remote",
                "expected_result": False,
            },
            id="no_matching_keywords",
        ),
        # matching keyword but no matching region
        pytest.param(
            {
                "title": "Python Developer",
                "description": "Looking for a developer",
                "region": "usa only",
                "tags": [],
                "keywords": {"python"},
                "expected_region": "remote",
                "expected_result": False,
            },
            id="no_matching_region",
        ),
    ],
)
def test_validate_keywords_and_region(placeholder_portal, test_case):
    with (
        patch.object(config, "KEYWORDS", test_case["keywords"]),
        patch.object(config, "REGION", test_case["expected_region"]),
    ):
        result = placeholder_portal.validate_keywords_and_region(
            link="https://example.com",
            title=test_case["title"],
            description=test_case["description"],
            region=test_case["region"],
            tags=test_case["tags"],
        )

    assert result == test_case["expected_result"]


@pytest.mark.parametrize(
    "test_case",
    [
        # Valid salary above minimum
        pytest.param(
            {
                "salary_value": "100000",
                "min_salary": Decimal("50000"),
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
        # Valid salary below minimum
        pytest.param(
            {
                "salary_value": "40000",
                "min_salary": Decimal("50000"),
                "expected_result": None,
            },
            id="salary_below_minimum",
        ),
        # Invalid salary format
        pytest.param(
            {
                "salary_value": "negotiable",
                "min_salary": Decimal("50000"),
                "expected_result": None,
            },
            id="invalid_salary_format",
        ),
        # None salary
        pytest.param(
            {
                "salary_value": None,
                "min_salary": Decimal("50000"),
                "expected_result": None,
            },
            id="no_salary",
        ),
    ],
)
def test_validate_salary(placeholder_portal, test_case):
    with patch.object(config, "SALARY", test_case["min_salary"]):
        result = placeholder_portal.validate_salary(
            link="https://example.com", salary=test_case["salary_value"]
        )

    assert result == test_case["expected_result"]
