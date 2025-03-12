import pytest
from decimal import Decimal

from job_notifier.portals.weworkremotely import WeWorkRemotely
from job_notifier.base import Message

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
                <link>{JOB_URL}/job-with-salary-greater-than-60K</link>
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


def test_get_messages_to_notify(mock_job_page, httpx_mock, mock_rss_response):
    portal = WeWorkRemotely()

    httpx_mock.add_response(
        url=portal.url,
        content=mock_rss_response,
    )
    httpx_mock.add_response(
        url=f"{JOB_URL}/job-with-salary-greater-than-60K",
        content=mock_job_page(salary=Decimal(str(80_000))),
    )
    httpx_mock.add_response(
        url=f"{JOB_URL}/job-with-salary-less-than-60K",
        content=mock_job_page(salary=Decimal(str(50_000))),
    )
    httpx_mock.add_response(
        url=f"{JOB_URL}/job-without-salary",
        content="<div></div>",
    )
    httpx_mock.add_response(
        url=f"{JOB_URL}/salary-missing",
        content="<div>salary:</div>",
    )

    messages_to_notify = portal.get_messages_to_notify()
    assert messages_to_notify == [
        Message(
            title="Python Developer",
            link="https://weworkremotely.com/jobs/job-with-salary-greater-than-60K",
            salary=Decimal(str(80_000)),
            posted_on="5 days ago",
        ),
    ]
