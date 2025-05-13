from datetime import datetime
from datetime import timedelta
from datetime import timezone
from unittest.mock import patch

import httpx
import pytest

from job_board.base import Job
from job_board.portals import Himalayas


@pytest.mark.xfail(reason="Need to fix this with the asyncio implementation")
def test_get_jobs(respx_mock, load_response):
    portal = Himalayas()
    # so that tests don't fail in future due to the date check.
    portal.validate_recency = lambda **kwargs: True

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
        patch("tenacity.nap.time.sleep") as mocked_sleep,
        patch.object(Himalayas, "_REQUEST_BATCH_SIZE", 1),
    ):
        jobs = portal.get_jobs()

    mocked_sleep.assert_called_once()

    assert len(jobs) == 40
    # just pick any one job from the list
    # each of them will have the same structure
    job = jobs[0]
    assert isinstance(job, Job)
    assert job.title == "Arabic/English UX Writer"
    assert (
        job.link
        == "https://himalayas.app/companies/tabby/jobs/arabic-english-ux-writer"
    )
    assert job.salary is None
    assert job.posted_on == datetime(
        year=2025, month=4, day=8, hour=14, minute=34, second=32, tzinfo=timezone.utc
    )
    assert job.tags == ["UX", "Writer", "Senior", "UX", "Writer"]
    assert job.locations == ["Jordan"]
    assert job.is_remote is False
    assert job.description is not None

    portal.last_run_at = datetime.now(tz=timezone.utc) + timedelta(days=1)
    respx_mock.get(portal.url).mock(
        side_effect=[
            httpx.Response(text=page_1, status_code=200),
            # httpx.Response(text=page_2, status_code=200),
        ]
    )

    with patch.object(Himalayas, "_REQUEST_BATCH_SIZE", 2):
        # this should return no jobs since the last_run_at is in future
        jobs = portal.get_jobs()

    assert len(jobs) == 20
