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
    "title" : "Senior Software Engineer, AI Model serving",
    "description" : "&lt;p&gt;&lt;strong&gt;Overview&lt;/strong&gt;&lt;/p&gt;
&lt;p data-speechify-sentence=&quot;&quot;&gt;As Speechify expands, our AI team seeks a Senior Backend Engineer. This role is central to ensuring our infrastructure scales efficiently, optimizing key product flows, and constructing resilient end-to-end systems. If you are passionate about strategizing, enjoy high-paced environments, and are eager to take ownership of product decisions, we&amp;rsquo;d love to hear from you.&lt;/p&gt;
&lt;p&gt;&lt;strong&gt;What Yo&lt;/strong&gt;&lt;strong&gt;u&amp;rsquo;&lt;/strong&gt;&lt;strong&gt;ll Do&lt;/strong&gt;&lt;/p&gt;
&lt;ul&gt;
&lt;li data-speechify-sentence=&quot;&quot;&gt;State of the art voice cloning&lt;/li&gt;
&lt;li data-speechify-sentence=&quot;&quot;&gt;Low latency and cost effective text to speech&lt;/li&gt;
&lt;/ul&gt;
&lt;p&gt;&lt;strong&gt;An Ideal Candidate Should Have&lt;/strong&gt;&lt;/p&gt;
&lt;ul&gt;
&lt;li&gt;Proven experience in backend development: Python&lt;/li&gt;
&lt;li&gt;Direct experience with GCP and knowledge of AWS, Azure, or other cloud providers.&lt;/li&gt;
&lt;li&gt;Efficiency in ideation and implementation, prioritizing tasks based on urgency and impact.&lt;/li&gt;
&lt;li&gt;Experience with Docker and containerized deployments.&lt;/li&gt;
&lt;li&gt;Proficiency in deploying high availability applications on Kubernetes.&lt;/li&gt;
&lt;li&gt;Preferred: Experience deploying NLP or TTS models to production.&lt;/li&gt;
&lt;/ul&gt;
&lt;p data-speechify-sentence=&quot;&quot;&gt;&lt;strong&gt;What We Offer&lt;/strong&gt;&lt;/p&gt;
&lt;ul&gt;
&lt;li&gt;A dynamic environment where your contributions shape the company and its products.&lt;/li&gt;
&lt;li&gt;A team that values innovation, intuition, and drive.&lt;/li&gt;
&lt;li&gt;Autonomy, fostering focus and creativity.&lt;/li&gt;
&lt;li&gt;The opportunity to have a significant impact in a revolutionary industry.&lt;/li&gt;
&lt;li&gt;Competitive compensation, a welcoming atmosphere, and a commitment to an exceptional asynchronous work culture.&lt;/li&gt;
&lt;li&gt;The privilege of working on a product that changes lives, particularly for those with learning differences like dyslexia, ADD, and more.&lt;/li&gt;
&lt;li&gt;An active role at the intersection of artificial intelligence and audio &amp;ndash; a rapidly evolving tech domain.&lt;/li&gt;
&lt;/ul&gt;
&lt;p&gt;&lt;strong&gt;Compensation:&amp;nbsp;&lt;/strong&gt;The US base salary range for this full-time position is $140,000-$200,000 + bonus + equity depending on experience&lt;/p&gt;
&lt;p&gt;&lt;strong&gt;Think you&amp;rsquo;re a good fit for this job?&amp;nbsp;&lt;/strong&gt;&lt;/p&gt;
&lt;p&gt;Tell us more about yourself and why you&#39;re interested in the role when you apply.&lt;br&gt;And don&amp;rsquo;t forget to include links to your portfolio and LinkedIn.&lt;/p&gt;
&lt;p&gt;&lt;strong&gt;Not looking but know someone who would make a great fit?&amp;nbsp;&lt;/strong&gt;&lt;/p&gt;
&lt;p&gt;Refer them!&amp;nbsp;&lt;/p&gt;
&lt;p&gt;&lt;strong&gt;Speechify is committed to a diverse and inclusive workplace.&amp;nbsp;&lt;/strong&gt;&lt;/p&gt;
&lt;p&gt;Speechify does not discriminate on the basis of race, national origin, gender, gender identity, sexual orientation, protected veteran status, disability, age, or other legally protected status.&lt;/p&gt;",
    "datePosted" : "2025-07-09 15:39:57 UTC",
    "validThrough" : "2025-09-07 15:39:57 UTC",
    "employmentType" : "Contract",
    "directApply": "False",
    "occupationalCategory": "Back-End Programming",
    "url": "http://www.speechify.com",
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
      "applicantLocationRequirements" : [
        {"@type":"Country","name":"AF"},
        {"@type":"Country","name":"AX"},
        {"@type":"Country","name":"AL"}
      ],
    "hiringOrganization" : {
      "@type" : "Organization",
      "name" : "Speechify Inc",
      "address": "Florida",
      "sameAs" : "http://www.speechify.com"
    },
    "identifier": {
      "@type": "PropertyValue",
      "name": "Speechify Inc",
      "value": "speechify-inc-senior-software-engineer-ai-model-serving"
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
        content='<script type="application/ld+json">{"hiringOrganization" : {"name" : "Speechify Inc"}}</script><div></div>',  # noqa: E501
    )
    mock_scrapfly_response(
        url=f"{JOB_URL}/job-salary-missing",
        content='<script type="application/ld+json">{"hiringOrganization" : {"name" : "Speechify Inc"}}</script><div>salary:</div>',  # noqa: E501
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
    assert job.locations == ["AF", "AX", "AL"]
    assert job.tags == ["c#"]
    assert job.company_name == "Speechify Inc"


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
