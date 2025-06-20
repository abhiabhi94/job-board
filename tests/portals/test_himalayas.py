import asyncio
import re
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from unittest.mock import patch

import httpx

from job_board import config
from job_board.portals import Himalayas
from job_board.portals.parser import Job
from job_board.utils import EXCHANGE_RATE_API_URL


def test_get_jobs(respx_mock, load_response):
    portal = Himalayas()
    # so that tests don't fail in future due to the date check.
    portal.validate_recency = lambda x: True

    exchange_rate_url_pattern = re.compile(
        EXCHANGE_RATE_API_URL.format(currency="usd", date=r"\d{4}-\d{2}-\d{2}"),
        flags=re.IGNORECASE,
    )
    respx_mock.get(exchange_rate_url_pattern).mock(
        return_value=httpx.Response(
            status_code=200,
            json={
                "usd": {
                    "inr": 0.012,
                    "cad": 0.015,
                }
            },
        )
    )

    page_1 = load_response("himalayas-page-1.json")
    page_2 = load_response("himalayas-page-2.json")

    respx_mock.get(portal.url).mock(
        side_effect=[
            httpx.Response(text=page_1, status_code=200),
            httpx.Response(text="", status_code=429),
            httpx.Response(text=page_2, status_code=200),
        ]
    )

    with (
        patch.object(asyncio, "sleep") as mocked_sleep,
        patch.object(config, "HIMALAYAS_REQUESTS_BATCH_SIZE", 1),
    ):
        jobs = portal.get_jobs()

    mocked_sleep.assert_called_once()

    assert len(jobs) == 40
    # just pick any one job from the list
    # each of them will have the same structure
    job = jobs[0]
    assert isinstance(job, Job)
    assert job.title == "Data Analyst (Punjabi Speaker)"
    assert (
        job.link
        == "https://himalayas.app/companies/peroptyx/jobs/data-analyst-punjabi-speaker"
    )
    assert job.salary is None
    assert job.posted_on == datetime(
        year=2025, month=6, day=10, hour=8, minute=30, second=27, tzinfo=timezone.utc
    )
    assert job.tags == ["data", "analyst", "data science"]
    assert job.locations == ["India"]
    assert job.is_remote is False
    assert job.description is not None

    portal.last_run_at = datetime.now(tz=timezone.utc) + timedelta(days=1)
    respx_mock.get(portal.url).mock(
        side_effect=[
            httpx.Response(text=page_1, status_code=200),
            httpx.Response(text=page_2, status_code=200),
        ]
    )

    # this should return just the results from the first page
    # since the last_run_at is set to a future date
    jobs = portal.get_jobs()

    assert len(jobs) == 20
