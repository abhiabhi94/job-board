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
    jobs = portal.get_jobs()
    assert len(jobs) == 20
    job = jobs[0]

    assert job.title == "Senior Full-stack Developer (Python, React, Elixir), Lemon.io"
    assert job.link == "https://www.python.org/jobs/7831/"
    assert job.description is not None
    assert job.salary is None
    assert job.posted_on is None
    assert job.tags == ["python"]
    assert job.is_remote is False
    assert job.locations == ["CLAYMONT, Utah, United States"]
