import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

import httpx
from pytest_httpx import HTTPXMock
from freezegun import freeze_time

from job_notifier.portals.remotive import Remotive
from job_notifier import config


@pytest.fixture
def portal():
    return Remotive()


@pytest.fixture
def sample_job():
    return {
        "url": "https://remotive.com/jobs/123",
        "title": "Python Developer",
        "description": (
            "<p>We are looking for a Python developer with 3+ years of experience.</p>"
        ),
        "candidate_required_location": "Worldwide",
        "tags": ["python", "django", "api"],
        "salary": "90000-120000",
        "publication_time": "2024-03-13T10:00:00",
    }


@pytest.fixture
def sample_jobs_response(sample_job):
    return {
        "jobs": [
            sample_job,
            # no matching keywords
            {
                "url": "https://remotive.com/jobs/124",
                "title": "Java Developer",
                "description": "<p>We are looking for a Java developer.</p>",
                "candidate_required_location": "Worldwide",
                "tags": ["java", "spring"],
                "salary": "100000-130000",
                "publication_time": "2024-03-13T11:00:00",
            },
            # matching keywords but low salary
            {
                "url": "https://remotive.com/jobs/125",
                "title": "Junior Python Developer",
                "description": "<p>Entry level position.</p>",
                "candidate_required_location": "Worldwide",
                "tags": ["python"],
                "salary": "40000-50000",
                "publication_time": "2024-03-13T12:00:00",
            },
            # no salary info
            {
                "url": "https://remotive.com/jobs/126",
                "title": "Python Developer",
                "description": "<p>We need a Python expert.</p>",
                "candidate_required_location": "Worldwide",
                "tags": ["python"],
                "publication_time": "2024-03-13T13:00:00",
            },
        ]
    }


def test_get_messages_to_notify(httpx_mock: HTTPXMock, portal, sample_jobs_response):
    httpx_mock.add_response(
        url=portal.url, method="GET", json=sample_jobs_response, status_code=200
    )

    with (
        patch.object(config, "KEYWORDS", {"python"}),
        patch.object(config, "REGION", "remote"),
        patch.object(config, "SALARY", Decimal(str(60_000))),
    ):
        messages = portal.get_messages_to_notify()

    (message,) = messages
    assert message.link == "https://remotive.com/jobs/123"
    assert message.title == "Python Developer"
    assert message.salary == Decimal(str(120_000))
    assert message.posted_on == datetime(2024, 3, 13, 10, 0, 0)


def test_get_message_to_notify_valid_job(portal, sample_job):
    with (
        patch.object(config, "KEYWORDS", {"python"}),
        patch.object(config, "REGION", "remote"),
        patch.object(config, "SALARY", Decimal("60000")),
        freeze_time("2024-03-13"),
    ):
        message = portal.get_message_to_notify(sample_job)

    assert message.link == "https://remotive.com/jobs/123"
    assert message.title == "Python Developer"
    assert message.salary == Decimal("120000")
    assert message.posted_on == datetime(2024, 3, 13, 10, 0, 0)


def test_get_message_to_notify_invalid_keywords(portal, sample_job):
    with (
        patch.object(config, "KEYWORDS", {"java"}),
        patch.object(config, "REGION", "remote"),
        patch.object(config, "SALARY", Decimal("60000")),
    ):
        message = portal.get_message_to_notify(sample_job)

    assert message is None


def test_get_message_to_notify_invalid_region(portal, sample_job):
    sample_job["candidate_required_location"] = "USA Only"

    with (
        patch.object(config, "KEYWORDS", {"python"}),
        patch.object(config, "REGION", "remote"),
        patch.object(config, "SALARY", Decimal("60000")),
    ):
        message = portal.get_message_to_notify(sample_job)
    assert message is None


def test_get_message_to_notify_when_job_salary_is_lower_than_config_salary(
    portal, sample_job
):
    salary = Decimal(str(150_000))
    assert salary > Decimal(sample_job["salary"].split("-")[-1].strip())

    with (
        patch.object(config, "KEYWORDS", {"python"}),
        patch.object(config, "REGION", "remote"),
        patch.object(config, "SALARY", salary),
    ):
        message = portal.get_message_to_notify(sample_job)

    assert message is None


def test_get_message_to_notify_no_salary(portal, sample_job):
    sample_job.pop("salary")

    with (
        patch.object(config, "KEYWORDS", {"python"}),
        patch.object(config, "REGION", "remote"),
        patch.object(config, "SALARY", Decimal("60000")),
    ):
        message = portal.get_message_to_notify(sample_job)

    assert message is None


def test_get_message_to_notify_invalid_salary_format(portal, sample_job):
    sample_job["salary"] = "negotiable"

    with (
        patch.object(config, "KEYWORDS", {"python"}),
        patch.object(config, "REGION", "remote"),
        patch.object(config, "SALARY", Decimal("60000")),
    ):
        message = portal.get_message_to_notify(sample_job)

    assert message is None


def test_api_error_handling(httpx_mock: HTTPXMock, portal):
    httpx_mock.add_response(url=portal.url, method="GET", status_code=500)

    with pytest.raises(httpx.HTTPStatusError):
        portal.get_messages_to_notify()
