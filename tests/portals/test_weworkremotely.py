import re
from datetime import datetime
from datetime import timezone
from decimal import Decimal

import httpx
import pytest
from lxml import html

from job_board.portals import WeWorkRemotely
from job_board.portals.weworkremotely import Parser
from job_board.utils import EXCHANGE_RATE_API_URL
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
    def _mock_job_page():
        job_page_content = """
        <script type="application/ld+json"> {
    "@context" : "http://schema.org/",
    "@type" : "JobPosting",
    "title" : "Mid-Senior Rails Systems Monitoring &amp; Quality Assurance ",
       "image": "https://we-work-remotely.imgix.net/logos/0170/7458/logo.gif?ixlib=rails-4.0.0&w=50&h=50&dpr=2&fit=fill&auto=compress",
    "description" : "Apply now and help us take our development to the next level.&lt;/p&gt;",
    "datePosted" : "2025-04-11 23:05:46 UTC",
    "validThrough" : "2025-09-08 23:05:46 UTC",
    "employmentType" : "Full-Time",
    "directApply": "False",
    "occupationalCategory": "Back-End Programming",
    "url": "https://webpunch.com/",
      "jobLocation": {
        "@type": "Place",
        "address": {
          "@type": "PostalAddress",
          "addressLocality": "Germany"
        }
      },
    "jobLocationType": "TELECOMMUTE",
    "baseSalary" : {
      "@type": "MonetaryAmount",
      "currency" : "USD",
      "value": {
        "@type": "QuantitativeValue",
        "minValue": "0",
        "maxValue": "0",
        "unitText":"YEAR"
      }
    },
      "applicantLocationRequirements" : [{"@type":"Country","name":"AU"},{"@type":"Country","name":"CA"},{"@type":"Country","name":"CH"},{"@type":"Country","name":"DE"},{"@type":"Country","name":"FR"},{"@type":"Country","name":"GB"},{"@type":"Country","name":"HK"},{"@type":"Country","name":"IT"},{"@type":"Country","name":"JP"},{"@type":"Country","name":"MX"},{"@type":"Country","name":"US"}],
    "hiringOrganization" : {
      "@type" : "Organization",
      "name" : "WebPunch",
      "address": "Denver, CO",
      "sameAs" : "https://webpunch.com/"
        , "logo": "https://we-work-remotely.imgix.net/logos/0170/7458/logo.gif?ixlib=rails-4.0.0&w=50&h=50&dpr=2&fit=fill&auto=compress"
    },
    "identifier": {
      "@type": "PropertyValue",
      "name": "WebPunch",
      "value": "webpunch-mid-senior-rails-systems-monitoring-quality-assurance"
    }
  }
  </script>
        <title>Python Developer</title>
        <p> Something happened 6 days ago, this is not the date of posting </p>
        <span> Posted 5 days ago </span>
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


def test_fetch_jobs(
    mock_job_page,
    mock_rss_response,
    mock_scrapfly_response,
    db_session,
):
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

    jobs = portal.fetch_jobs()

    assert len(jobs) == 4
    # just pick the first job to check the values
    job = jobs[0]
    assert job.title == "Python Developer"
    assert job.link == "https://weworkremotely.com/jobs/job-1"
    assert job.description == "Looking for Django and FastAPI developer"
    assert job.min_salary is None
    assert job.max_salary is None
    assert job.posted_on == datetime(
        year=2025, month=4, day=14, hour=13, minute=12, second=48, tzinfo=timezone.utc
    )
    assert job.is_remote is True
    assert job.locations == [
        "AU",
        "CA",
        "CH",
        "DE",
        "FR",
        "GB",
        "HK",
        "IT",
        "JP",
        "MX",
        "US",
    ]
    assert job.tags == ["c#"]


@pytest.mark.parametrize(
    ("salary_info, min_salary, max_salary"),
    [
        ("$80,000", Decimal("80000"), None),
        ("$80,000 - $100,000", Decimal("80000"), Decimal("100000")),
        ("$100K or more USD", Decimal("100000"), None),
        ("$100,000 or more CAD", Decimal("73529.41"), None),
        ("", None, None),  # No salary info
    ],
)
def test_get_salary_range(
    salary_info, min_salary, max_salary, respx_mock, load_response
):
    parser = Parser(api_data_format="xml", item={})
    parser.get_posted_on = lambda: datetime.now(timezone.utc)
    parser.get_link = lambda: "https://weworkremotely.com/jobs/job-1"
    response = load_response("weworkremotely.html").replace("$SALARY_INFO", salary_info)
    parser.extra_info = html.fromstring(response)
    exchange_rate_url_pattern = re.compile(
        EXCHANGE_RATE_API_URL.format(currency="usd", date=r"\d{4}-\d{2}-\d{2}"),
        flags=re.IGNORECASE,
    )
    respx_mock.get(exchange_rate_url_pattern).mock(
        return_value=httpx.Response(
            status_code=200,
            json={
                "usd": {
                    "cad": 1.36,
                }
            },
        )
    )

    salary_range = parser.get_salary_range()
    assert salary_range.min_salary.amount == min_salary
    if salary_range.min_salary.amount is not None:
        assert salary_range.min_salary.currency == "USD"
    assert salary_range.max_salary.amount == max_salary
