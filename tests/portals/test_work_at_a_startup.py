from decimal import Decimal

import httpx

from job_board.base import Job
from job_board.portals import WorkAtAStartup
from job_board.portals.work_at_a_startup import ALGOLIA_URL


def test_get_jobs(respx_mock, load_response):
    portal = WorkAtAStartup()

    respx_mock.post(ALGOLIA_URL).mock(
        return_value=httpx.Response(
            text=load_response("work-at-a-startup-algolia.json"),
            status_code=200,
        )
    )
    respx_mock.post(portal.url).mock(
        return_value=httpx.Response(
            text=load_response("work-at-a-startup.json"),
            status_code=200,
        )
    )

    jobs = portal.get_jobs()

    assert len(jobs) == 7
    # just pick one, each of them will have the same structure
    job = jobs[0]
    assert isinstance(job, Job)
    assert job.title == "Senior Engineer - ML & AI"
    assert job.link == "https://www.workatastartup.com/jobs/64051"
    assert job.salary == Decimal(str(120_000))
    assert job.posted_on is None
