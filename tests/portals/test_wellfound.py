from unittest.mock import patch
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import httpx

import pytest

from job_board import config
from job_board.base import Job
from job_board.portals.wellfound import (
    Wellfound,
)
from job_board.utils import (
    SCRAPFLY_URL,
    ScrapflyError,
)


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
        "locationNames": ["Remote", "India"],
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

    page_1 = load_response("wellfound-page-1.html")
    page_2 = load_response("wellfound-page-2.html")
    respx_mock.get(SCRAPFLY_URL).mock(
        side_effect=[
            httpx.Response(
                status_code=200,
                json={
                    "result": {
                        "content": page_1,
                        "success": True,
                        "log_url": "https://scrapfly.io/dashboard/monitoring/log/01JSSF871YYCVQJY9MPFTGPF77",
                    }
                },
            ),
            httpx.Response(
                status_code=200,
                json={
                    "result": {
                        "content": page_2,
                        "success": True,
                        "log_url": "https://scrapfly.io/dashboard/monitoring/log/01JSSJ7SNMEEJJDP0JPAACQ03D",
                    }
                },
            ),
        ]
    )

    jobs = wellfound.get_jobs()

    assert len(jobs) == 2
    # just pick any one job from the list
    # each of them will have the same structure
    job = jobs[0]

    assert isinstance(job, Job)
    assert "Python" in job.title
    assert "python" in job.link
    assert job.salary >= config.SALARY
    assert job.posted_on is not None


def test_scrapfly_api_returns_non_successfull_response(
    wellfound, load_response, respx_mock
):
    respx_mock.get(SCRAPFLY_URL).mock(
        return_value=httpx.Response(
            status_code=200,
            json={
                "result": {
                    "success": False,
                    "status_code": 403,
                    "log_url": "https://scrapfly.io/dashboard/monitoring/log/01JSSF871YYCVQJY9MPFTGPF77",
                    "error": {
                        "message": "Forbidden",
                        "retryable": False,
                    },
                    "url": "https://wellfound.com/jobs",
                    "content": "",
                    "response_headers": {
                        "Content-Type": "text/html; charset=utf-8",
                    },
                }
            },
        ),
    )

    with pytest.raises(ScrapflyError) as excinfo:
        wellfound.get_jobs()

    assert excinfo.value.message == "Forbidden"
    assert excinfo.value.request.method == "GET"
    assert excinfo.value.request.url == "https://wellfound.com/jobs"
    assert excinfo.value.response.status_code == 403
    assert excinfo.value.is_retryable is False
