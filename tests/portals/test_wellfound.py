from datetime import datetime
from datetime import timezone
from unittest.mock import patch

import httpx
import pytest

from job_board.base import Job
from job_board.portals.wellfound import (
    Wellfound,
)
from job_board.utils import SCRAPFLY_URL
from job_board.utils import ScrapflyError


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


def test_get_jobs(wellfound, load_response, respx_mock):
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
                        "content": "",
                        "status_code": 403,
                        "response_headers": {},
                        "url": wellfound.url,
                        "success": False,
                        "error": {
                            "message": "The website responded with a 403 status code",
                            "retryable": True,
                        },
                        "log_url": "https://scrapfly.io/dashboard/monitoring/log/01JSSF871YYCVQJY9MPFTGPF78",
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

    with patch("tenacity.nap.time.sleep") as mocked_sleep:
        jobs = wellfound.get_jobs()

    mocked_sleep.assert_called_once()

    assert len(jobs) == 52
    # just pick any one job from the list
    # each of them will have the same structure
    job = jobs[0]

    assert isinstance(job, Job)
    assert job.title == "Python Developer"
    assert job.description is not None
    assert job.link == "https://wellfound.com/jobs/2747178-python-developer"
    assert job.salary is None
    assert job.posted_on == datetime(
        year=2023, month=7, day=26, hour=9, minute=46, second=39, tzinfo=timezone.utc
    )
    assert job.tags == []
    assert job.locations == ["India"]
    assert job.is_remote is True


def test_scrapfly_api_returns_non_successful_response(wellfound, respx_mock):
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

    with (
        pytest.raises(ScrapflyError) as excinfo,
        patch("tenacity.nap.time.sleep") as mocked_sleep,
    ):
        wellfound.get_jobs()

    assert mocked_sleep.call_count == 4

    assert excinfo.value.message == "Forbidden"
    assert excinfo.value.request.method == "GET"
    assert excinfo.value.request.url == "https://wellfound.com/jobs"
    assert excinfo.value.response.status_code == 403
    assert excinfo.value.is_retryable is False
