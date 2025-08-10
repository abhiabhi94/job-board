import re
from datetime import date

import httpx
import pytest

from job_board.portals import PythonDotOrg


def test_fetch_jobs(
    respx_mock,
    load_response,
    db_session,
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
    assert job.locations == ["US-UT", "US"]


@pytest.mark.parametrize(
    "locations, expected_iso_codes",
    [
        ("USA, Canada", ["US", "CA"]),
        ("New York", ["US-NY"]),
        ("Remote", []),
    ],
)
def test_parse_locations(locations, expected_iso_codes):
    Parser = PythonDotOrg.parser_class
    iso_codes = Parser.parse_locations(locations)
    assert iso_codes == expected_iso_codes
