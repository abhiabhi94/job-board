import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from freezegun import freeze_time
import httpx

from job_board.portals.weworkremotely import WeWorkRemotely
from job_board.base import Job


JOB_URL = "https://weworkremotely.com/jobs"


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

    return rss_content.encode()


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


def test_get_jobs_to_notify(mock_job_page, respx_mock, mock_rss_response):
    portal = WeWorkRemotely()

    respx_mock.get(url=portal.url).mock(
        return_value=httpx.Response(content=mock_rss_response, status_code=200)
    )
    respx_mock.get(url=f"{JOB_URL}/job-with-salary-greater-than-60K").mock(
        return_value=httpx.Response(
            content=mock_job_page(salary=Decimal(str(80_000))),
            status_code=200,
        )
    )
    content = mock_job_page(salary=Decimal(str(90_000))).replace(
        "5 days ago", "1 hour ago"
    )
    respx_mock.get(url=f"{JOB_URL}/job-with-salary-greater-than-80K").mock(
        return_value=httpx.Response(content=content, status_code=200)
    )

    content = mock_job_page(salary=Decimal(str(10_000))).replace(
        "5 days ago", "a few minutes ago"
    )
    respx_mock.get(url=f"{JOB_URL}/job-added-just-now").mock(
        return_value=httpx.Response(content=content, status_code=200),
    )
    content = mock_job_page(salary=Decimal(str(200_000))).replace(
        "5 days ago", "45 minutes ago"
    )
    respx_mock.get(url=f"{JOB_URL}/job-added-45-minutes-ago").mock(
        return_value=httpx.Response(content=content, status_code=200)
    )
    respx_mock.get(url=f"{JOB_URL}/job-with-salary-less-than-60K").mock(
        return_value=httpx.Response(
            content=mock_job_page(salary=Decimal(str(50_000))),
            status_code=200,
        )
    )
    respx_mock.get(url=f"{JOB_URL}/job-without-salary").mock(
        return_value=httpx.Response(
            content="<div></div>",
            status_code=200,
        )
    )
    respx_mock.get(url=f"{JOB_URL}/salary-missing").mock(
        return_value=httpx.Response(
            content="<div>salary:</div>",
            status_code=200,
        )
    )

    now = datetime.now(timezone.utc)
    with freeze_time(now):
        job_listings_to_notify = portal.get_jobs_to_notify()

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
