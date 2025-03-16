import pytest
import json

import httpx
import openai_responses

from job_board.portals.remotive import Remotive
from job_board.base import JobListing


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


@openai_responses.mock()
def test_get_jobs_to_notify(
    respx_mock,
    sample_jobs_response,
    openai_mock: openai_responses.OpenAIMock,
    sample_job,
):
    respx_mock.get(Remotive.url).mock(
        return_value=httpx.Response(json=sample_jobs_response, status_code=200)
    )

    job_data = {
        "title": sample_job["title"],
        "salary": sample_job["salary"].split("-")[-1],
        "link": sample_job["url"],
        "location": sample_job["candidate_required_location"],
        "posted_on": "2025-01-01T00:00:00Z",
    }
    openai_mock.chat.completions.create.response = {
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"content": json.dumps([job_data]), "role": "assistant"},
            }
        ]
    }

    portal = Remotive()

    (result,) = portal.get_jobs_to_notify()

    assert result == JobListing(**job_data)
