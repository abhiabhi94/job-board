from unittest.mock import patch
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import httpx

import pytest

from job_board import config
from job_board.base import Job
from job_board.portals.wellfound import Wellfound


@pytest.fixture
def wellfound():
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
    ("job_data", "config_salary"),
    [
        # non-remote job
        ({"remote": False}, Decimal(str(100_000))),
        # without compensation
        ({"compensation": ""}, Decimal(str(100_000))),
        # below salary threshold
        ({"compensation": "$100k – $150k • details"}, Decimal(str(200_000))),
        # invalid salary i.e doesn't match the expected salary format.
        ({"compensation": "₹10,000 – ₹15,000"}, Decimal(str(200_000))),
        # no salary info
        ({"compensation": "No Equity"}, Decimal(str(200_000))),
        # too old job
        (
            {
                "liveStartAt": (
                    datetime.now(tz=timezone.utc) - timedelta(days=365)
                ).timestamp(),
            },
            Decimal(str(200_000)),
        ),
        # non-matching keywords
        (
            {
                "title": "Typescript Developer",
                "description": "Job description",
            },
            Decimal(str(200_000)),
        ),
    ],
)
def test_filter_job_invalid(wellfound, job_data, config_salary):
    job_result = create_job_result(job_data)

    with patch.object(config, "SALARY", config_salary):
        job = wellfound.filter_job(job_result)

    assert job is None


def test_filter_jobs_valid(wellfound, load_response, respx_mock):
    # so that tests don't fail in future due to the date check.
    wellfound.validate_recency = lambda **kwargs: True

    page_1 = load_response("wellfound-page-1.json")
    page_2 = load_response("wellfound-page-2.json")
    respx_mock.post(wellfound.url).mock(
        side_effect=[
            httpx.Response(text=page_1, status_code=200),
            httpx.Response(text=page_2, status_code=200),
        ]
    )

    jobs = wellfound.get_jobs()

    assert len(jobs) == 3
    # just pick any one job from the list
    # each of them will have the same structure
    job = jobs[0]

    assert isinstance(job, Job)
    assert "Python" in job.title
    assert "python" in job.link
    assert job.salary >= config.SALARY
    assert job.posted_on is not None

    respx_mock.post(wellfound.url).mock(
        return_value=httpx.Response(text=page_1, status_code=200)
    )
    wellfound.last_run_at = datetime.now(tz=timezone.utc)
    jobs = wellfound.get_jobs()
    assert len(jobs) == 2  # only the jobs from the first page.
