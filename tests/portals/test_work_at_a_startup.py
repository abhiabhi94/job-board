from decimal import Decimal

import httpx

from job_board.portals import WorkAtAStartup
from job_board.portals.parser import Job
from job_board.portals.work_at_a_startup import ALGOLIA_URL
from job_board.utils import EXCHANGE_RATE_API_URL
from job_board.utils import utcnow_naive


def test_fetch_jobs(
    respx_mock,
    load_response,
    db_session,
):
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
    url = EXCHANGE_RATE_API_URL.format(
        date=utcnow_naive().strftime("%Y-%m-%d"),
        currency="usd",
    )
    respx_mock.get(url).mock(
        return_value=httpx.Response(
            status_code=200,
            json={
                "usd": {
                    "inr": 82.8899448,
                    "cad": 1.35979219,
                }
            },
        )
    )

    jobs = portal.fetch_jobs()

    assert len(jobs) == 45
    # just pick one, each of them will have the same structure
    job = jobs[0]
    assert isinstance(job, Job)
    assert job.title == "CTO- Cyber Security"
    assert job.link == "https://www.workatastartup.com/jobs/63387"
    assert job.min_salary == Decimal(str(200_000))
    assert job.max_salary == Decimal(str(250_000))
    assert job.posted_on is None
    assert job.description is not None
    assert job.tags == []
    assert job.locations == []
