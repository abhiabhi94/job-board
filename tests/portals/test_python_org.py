from datetime import datetime
from decimal import Decimal

import httpx

from job_board.portals import PythonDotOrg


def test_get_jobs(respx_mock, load_response):
    sample_rss_feed = load_response("python_dot_org.rss")
    sample_jobs_html = load_response("python_jobs_sample.html")

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
