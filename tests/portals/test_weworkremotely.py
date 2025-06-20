from datetime import datetime
from datetime import timezone
from decimal import Decimal

import httpx
import pytest

from job_board.portals import WeWorkRemotely
from job_board.utils import SCRAPFLY_URL


JOB_URL = "https://weworkremotely.com/jobs"


@pytest.fixture
def mock_scrapfly_response(respx_mock):
    def _mock_scrapfly_response(url, content):
        respx_mock.get(SCRAPFLY_URL, params={"url": url}).mock(
            return_value=httpx.Response(
                status_code=200,
                json={
                    "result": {
                        "success": True,
                        "log_url": "https://scrapfly.com/dashboard/monitoring/something",
                        "content": content,
                    }
                },
            )
        )

    return _mock_scrapfly_response


@pytest.fixture
def mock_rss_response():
    rss_content = f"""<?xml version="1.0" encoding="UTF-8" ?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Python Developer</title>
                <description>Looking for Django and FastAPI developer</description>
                <region>Anywhere in the World</region>
                <link>{JOB_URL}/job-1</link>
                <pubDate>Mon, 14 Apr 2025 13:12:48 +0000</pubDate>
            </item>
            <item>
                <title>Python Developer</title>
                <description>Looking for Django and FastAPI developer</description>
                <region>Anywhere in the World</region>
                <link>{JOB_URL}/job-2</link>
                <pubDate>Sun, 16 Jun 2024 17:30:51 +0000</pubDate>
            </item>
            <item>
                <title>Python Developer</title>
                <description>Looking for Django and FastAPI developer</description>
                <region>Anywhere in the World</region>
                <link>{JOB_URL}/job-without-salary</link>
                <pubDate>Sun, 16 Jun 2024 17:30:51 +0000</pubDate>
            </item>
            <item>
                <title>Python Developer</title>
                <description>Looking for Django and FastAPI developer</description>
                <region>Anywhere in the World</region>
                <link>{JOB_URL}/job-salary-missing</link>
                <pubDate>Sun, 16 Jun 2024 17:30:51 +0000</pubDate>
            </item>
        </channel>
    </rss>"""

    return rss_content


@pytest.fixture
def mock_job_page():
    def _mock_job_page(salary=Decimal(str(80_000))):
        job_page_content = f"""
        <title>Python Developer</title>
        <p> Something happened 6 days ago, this is not the date of posting </p>
        <span> Posted 5 days ago </span>
        <div class="salary-class">
            <div>Salary: ${salary:,}</div>
        </div>
        <div class="lis-container__job__sidebar__job-about">
            <h4 class="lis-container__job__sidebar__job-about__title"> About the job </h4>
            <ul class="lis-container__job__sidebar__job-about__list">
                <li class="lis-container__job__sidebar__job-about__list__item"> Posted on <span>20 days ago</span></li>
                <li class="lis-container__job__sidebar__job-about__list__item"> Apply before <span>Jun 21th, 2025</span></li>
                <li class="lis-container__job__sidebar__job-about__list__item"> Job type <a target="_blank" href="/categories/remote-full-stack-programming-jobs"><span class="box box--jobType"><i class="fa-regular fa-clock" aria-hidden="true"></i> Full-Time </span></a></li>
                <li class="lis-container__job__sidebar__job-about__list__item"> Category <a target="_blank" href="/categories/remote-full-stack-programming-jobs"><span class="box box--blue">Full-Stack Programming</span></a></li>
                <li class="lis-container__job__sidebar__job-about__list__item lis-container__job__sidebar__job-about__list__item--full"> Region <div class="boxes"><a target="_blank" href="/100-percent-remote-jobs"><span class="box box--multi box--region"> Anywhere in the World </span></a></div></li>
                <li class="lis-container__job__sidebar__job-about__list__item lis-container__job__sidebar__job-about__list__item--full"></li>
                <li class="lis-container__job__sidebar__job-about__list__item lis-container__job__sidebar__job-about__list__item--full"> Skills <div class="boxes"><a target="_blank" href="/remote-jobs-c"><span class="box box--multi box--blue"> C# </span></a></div></li>
            </ul>
        </div>
        """  # noqa: E501
        return job_page_content

    return _mock_job_page


def test_get_jobs(mock_job_page, mock_rss_response, mock_scrapfly_response):
    portal = WeWorkRemotely()
    portal.parser_class.validate_recency = lambda x: True  # bypass recency check
    mock_scrapfly_response(
        url=portal.url,
        content=mock_rss_response,
    )

    mock_scrapfly_response(
        url=f"{JOB_URL}/job-1",
        content=mock_job_page(),
    )
    mock_scrapfly_response(
        url=f"{JOB_URL}/job-2",
        content=mock_job_page(),
    )

    mock_scrapfly_response(
        url=f"{JOB_URL}/job-without-salary",
        content="<div></div>",
    )
    mock_scrapfly_response(
        url=f"{JOB_URL}/job-salary-missing",
        content="<div>salary:</div>",
    )

    jobs = portal.get_jobs()

    assert len(jobs) == 4
    # just pick the first job to check the values
    job = jobs[0]
    assert job.title == "Python Developer"
    assert job.link == "https://weworkremotely.com/jobs/job-1"
    assert job.description == "Looking for Django and FastAPI developer"
    assert job.salary is None
    assert job.posted_on == datetime(
        year=2025, month=4, day=14, hour=13, minute=12, second=48, tzinfo=timezone.utc
    )
    assert job.is_remote is True
    assert job.locations == []
    assert job.tags == ["c#"]
