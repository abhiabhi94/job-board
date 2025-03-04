import pytest
from decimal import Decimal

from job_notifier.portals.weworkremotely import WeWorkRemotely

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
        <div class="{WeWorkRemotely.ABOUT_SECTION_CLASS}">
            <div>Salary: ${salary:,}</div>
        </div>
        """
        return job_page_content

    return _mock_job_page


def test_get_links_to_notify(mock_job_page, httpx_mock, mock_rss_response):
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
        content=f'<div class="{WeWorkRemotely.ABOUT_SECTION_CLASS}"></div>',
    )

    links_to_notify = portal.get_links_to_notify()
    assert links_to_notify == [
        "https://weworkremotely.com/jobs/job-with-salary-greater-than-60K",
    ]
