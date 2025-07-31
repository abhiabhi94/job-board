import re
from datetime import date

import httpx

from job_board.portals import PythonDotOrg


def test_fetch_jobs(
    respx_mock,
    load_response,
):
    sample_rss_feed = load_response("python_dot_org.rss")
    sample_jobs_html = load_response("python_sample_job.html")

    respx_mock.get(PythonDotOrg.url).mock(
        return_value=httpx.Response(text=sample_rss_feed, status_code=200)
    )

    respx_mock.get(PythonDotOrg.jobs_url).mock(
        return_value=httpx.Response(text=sample_jobs_html, status_code=200)
    )
    detail_page_re = re.compile(
        r"https://www.python.org/jobs/\d+/",
    )
    respx_mock.get(detail_page_re).mock(
        return_value=httpx.Response(text=sample_jobs_html, status_code=200)
    )

    portal = PythonDotOrg()
    jobs = portal.fetch_jobs()
    assert len(jobs) == 20
    job = jobs[0]

    assert job.title == "Senior Full-stack Developer (Python, React, Elixir), Lemon.io"
    assert job.link == "https://www.python.org/jobs/7831/"
    assert job.description is not None
    assert job.min_salary is None
    assert job.max_salary is None
    assert job.posted_on.date() == date(day=19, month=6, year=2025)
    assert job.tags == ["python", "cloud"]
    assert job.is_remote is False
    assert job.locations == ["CLAYMONT, Utah, United States"]
