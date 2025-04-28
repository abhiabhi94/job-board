import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from freezegun import freeze_time
import httpx

from job_board.portals import WeWorkRemotely
from job_board.base import Job
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
                <region>Anywhere</region>
                <link>{JOB_URL}/job-added-just-now</link>
            </item>
            <item>
                <title>Python Developer</title>
                <description>Looking for Django and FastAPI developer</description>
                <region>Anywhere</region>
                <link>{JOB_URL}/job-added-45-minutes-ago</link>
            </item>
            <item>
                <title>Python Developer</title>
                <description>Looking for Django and FastAPI developer</description>
                <region>Anywhere</region>
                <link>{JOB_URL}/job-with-salary-greater-than-60K</link>
            </item>
            <item>
                <title>Python Developer</title>
                <description>Looking for Django and FastAPI developer</description>
                <region>Anywhere</region>
                <link>{JOB_URL}/job-with-salary-greater-than-80K</link>
            </item>
            <item>
                <title>Python Developer</title>
                <description>Looking for Django and FastAPI developer</description>
                <region>Anywhere</region>
                <link>{JOB_URL}/job-with-salary-less-than-60K</link>
            </item>
            <item>
                <title>Python Developer</title>
                <description>Looking for Django and FastAPI developer</description>
                <region>Anywhere</region>
                <link>{JOB_URL}/job-without-salary</link>
            </item>
            <item>
                <title>Python Developer</title>
                <description>Looking for Django and FastAPI developer</description>
                <region>Anywhere</region>
                <link>{JOB_URL}/salary-missing</link>
            </item>
            <item>
                <title>React Developer</title>
                <description>Frontend role</description>
                <region>Anywhere</region>
                <link>https://unmocked-url.com</link>
            </item>
            <item>
                <title>React Developer</title>
                <description>Frontend role</description>
                <region>Anywhere</region>
                <link>https://unmocked-url.com</link>
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
        """
        return job_page_content

    return _mock_job_page


def test_get_jobs(mock_job_page, mock_rss_response, mock_scrapfly_response):
    portal = WeWorkRemotely()

    mock_scrapfly_response(url=portal.url, content=mock_rss_response)
    mock_scrapfly_response(
        url=f"{JOB_URL}/job-with-salary-greater-than-60K",
        content=mock_job_page(salary=Decimal(str(80_000))),
    )

    content = mock_job_page(salary=Decimal(str(90_000))).replace(
        "5 days ago", "1 hour ago"
    )
    mock_scrapfly_response(
        url=f"{JOB_URL}/job-with-salary-greater-than-80K",
        content=content,
    )

    content = mock_job_page(salary=Decimal(str(10_000))).replace(
        "5 days ago", "a few minutes ago"
    )
    mock_scrapfly_response(
        url=f"{JOB_URL}/job-added-just-now",
        content=content,
    )
    content = mock_job_page(salary=Decimal(str(200_000))).replace(
        "5 days ago", "45 minutes ago"
    )
    mock_scrapfly_response(
        url=f"{JOB_URL}/job-added-45-minutes-ago",
        content=content,
    )

    mock_scrapfly_response(
        url=f"{JOB_URL}/job-with-salary-less-than-60K",
        content=mock_job_page(salary=Decimal(str(50_000))),
    )
    mock_scrapfly_response(
        url=f"{JOB_URL}/job-without-salary",
        content="<div></div>",
    )
    mock_scrapfly_response(
        url=f"{JOB_URL}/salary-missing",
        content="<div>salary:</div>",
    )

    now = datetime.now(timezone.utc)
    with freeze_time(now):
        job_listings_to_notify = portal.get_jobs()

    assert job_listings_to_notify == [
        Job(
            title="Python Developer",
            link="https://weworkremotely.com/jobs/job-added-45-minutes-ago",
            salary=Decimal(str(200_000)),
            posted_on=now - timedelta(minutes=45),
        ),
        Job(
            title="Python Developer",
            link="https://weworkremotely.com/jobs/job-with-salary-greater-than-60K",
            salary=Decimal(str(80_000)),
            posted_on=now - timedelta(days=5),
        ),
        Job(
            title="Python Developer",
            link="https://weworkremotely.com/jobs/job-with-salary-greater-than-80K",
            salary=Decimal(str(90_000)),
            posted_on=now - timedelta(hours=1),
        ),
    ]
