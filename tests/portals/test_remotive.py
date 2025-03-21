from decimal import Decimal
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import pytest
import httpx
from freezegun import freeze_time

from job_board.portals import Remotive
from job_board.portals.remotive import DATE_FORMAT
from job_board.base import Job
from job_board.portals.base import JobsOpenAI, JobOpenAI


@pytest.fixture
def frozen_time():
    now = datetime.now(timezone.utc)
    with freeze_time(now):
        yield now.strftime(DATE_FORMAT)


@pytest.fixture
def sample_job(frozen_time):
    return {
        "url": "https://remotive.com/jobs/123",
        "title": "Python Developer",
        "description": (
            "<p>We are looking for a Python developer with 3+ years of experience.</p>"
        ),
        "candidate_required_location": "Worldwide",
        "tags": ["python", "django", "api"],
        "salary": "90000-120000",
        "publication_date": frozen_time,
    }


@pytest.fixture
def sample_jobs_response(sample_job, frozen_time):
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
                "publication_date": frozen_time,
            },
            # matching keywords but low salary
            {
                "url": "https://remotive.com/jobs/125",
                "title": "Junior Python Developer",
                "description": "<p>Entry level position.</p>",
                "candidate_required_location": "Worldwide",
                "tags": ["python"],
                "salary": "40000-50000",
                "publication_date": frozen_time,
            },
            # no salary info
            {
                "url": "https://remotive.com/jobs/126",
                "title": "Python Developer",
                "description": "<p>We need a Python expert.</p>",
                "candidate_required_location": "Worldwide",
                "tags": ["python"],
                "publication_date": frozen_time,
            },
        ]
    }


def test_get_jobs(
    respx_mock,
    sample_jobs_response,
    frozen_time,
):
    sample_job = {
        "title": "Software Engineer",
        "salary": "100000-150000",
        "url": "https://example.com/job",
        "candidate_required_location": "Remote",
        "publication_date": frozen_time,
    }
    job_data = {
        "title": sample_job["title"],
        "salary": Decimal(sample_job["salary"].split("-")[-1]),
        "link": sample_job["url"],
        "location": sample_job["candidate_required_location"],
        "posted_on": sample_job["publication_date"],
    }

    job_openai_instance = JobOpenAI(**job_data)
    jobs_openai_response = JobsOpenAI(jobs=[job_openai_instance])

    respx_mock.get(Remotive.url).mock(
        return_value=httpx.Response(json=sample_jobs_response, status_code=200)
    )

    with patch(
        "job_board.portals.base.openai.Client", autospec=True
    ) as mock_openai_class:
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response

        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_response.choices = [mock_choice]
        mock_choice.message = mock_message
        mock_message.parsed = jobs_openai_response

        portal = Remotive()

        (result,) = portal.get_jobs()

    assert result == Job(**job_data)
    assert mock_client.beta.chat.completions.parse.call_count == 1
