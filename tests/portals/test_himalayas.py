from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import httpx

from job_board.portals import Himalayas
from job_board.base import Job


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

    with patch("tenacity.nap.time.sleep") as mocked_sleep:
        (job,) = portal.get_jobs()

    mocked_sleep.assert_called_once()

    assert isinstance(job, Job)
    assert job.title == "Desenvolvedor Sênior (Python, Django, React)"
    assert (
        job.link
        == "https://himalayas.app/companies/spassu/jobs/desenvolvedor-senior-python-django-react-7926842257"
    )
    assert job.salary == Decimal(str(90_000))
    assert job.posted_on == datetime(
        year=2025, month=4, day=4, hour=16, minute=53, second=57, tzinfo=timezone.utc
    )

    portal.last_run_at = datetime.now(tz=timezone.utc) + timedelta(days=1)
    respx_mock.get(portal.url).mock(
        side_effect=[
            httpx.Response(text=page_1, status_code=200),
        ]
    )
    jobs = portal.get_jobs()
    assert jobs == []
