from datetime import datetime
from decimal import Decimal

import pytest
import httpx

from job_board.config import BASE_DIR
from job_board.portals import PythonDotOrg


@pytest.fixture
def sample_jobs_html():
    filepath = BASE_DIR / "tests/portals/responses" / "python_jobs_sample.html"
    with open(filepath, "r", encoding="utf-8") as file:
        return file.read()


@pytest.fixture
def sample_rss_feed():
    filepath = BASE_DIR / "tests/portals/responses" / "python_dot_org.rss"
    with open(filepath, "r", encoding="utf-8") as file:
        return file.read()


def test_get_jobs(respx_mock, sample_rss_feed, sample_jobs_html):
    respx_mock.get(PythonDotOrg.url).mock(
        return_value=httpx.Response(text=sample_rss_feed, status_code=200)
    )

    respx_mock.get(PythonDotOrg.jobs_url).mock(
        return_value=httpx.Response(text=sample_jobs_html, status_code=200)
    )

    portal = PythonDotOrg()
    (result,) = portal.get_jobs()

    assert result.title == "Full Stack Engineer (Django), Multi Media LLC"
    assert result.salary == Decimal(str(120_000))
    assert result.link == "https://www.python.org/jobs/7827/"
    assert result.posted_on == datetime.fromisoformat(
        "2025-02-27T22:42:21.713718+00:00"
    )
