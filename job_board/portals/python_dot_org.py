import httpx
from lxml import objectify
from datetime import datetime

from job_board.portals.base import (
    HOURLY_RATE_REGEX,
    RATE_REGEX,
    SALARY_RANGE_REGEX,
    SALARY_REGEX,
    BasePortal,
)
from job_board.base import Job
from lxml import html
from collections import defaultdict
from urllib.parse import urljoin


class PythonDotOrg(BasePortal):
    portal_name = "python_dot_org"
    base_url = "https://www.python.org"
    jobs_url = f"{base_url}/jobs/"
    url = f"{base_url}/jobs/feed/rss/"
    api_data_format = "xml"

    region_mapping = {
        "remote": {
            "remote",
            "worldwide",
            "anywhere",
            "global",
        },
    }

    def fetch_additional_info(self) -> dict[str, dict[str, datetime]]:
        # yeah this is awkward, but python dot org doesn't
        # provide the posted date in the rss feed
        job_details = defaultdict(dict)

        response = httpx.get(self.jobs_url)
        response.raise_for_status()

        tree = html.fromstring(response.text)
        for job in tree.cssselect("li"):
            # Extract the first <a> tag with href
            job_link = job.cssselect("a[href]")
            if not job_link:
                continue

            job_url = urljoin(self.base_url, job_link[0].get("href"))

            time_tag = job.cssselect("time[datetime]")
            if time_tag:
                job_details[job_url]["posted_on"] = time_tag[0].get("datetime")

        return dict(job_details)

    def get_jobs(self) -> list[Job]:
        job_details = self.fetch_additional_info()

        response = httpx.get(self.url)
        response.raise_for_status()
        return self.filter_jobs(data=response.content, job_details=job_details)

    def filter_jobs(self, data, job_details):
        root = objectify.fromstring(data)

        jobs: list[Job] = []
        for item in root.channel.item:
            if job := self.filter_job(item, job_details):
                jobs.append(job)
        return jobs

    def filter_job(self, item, job_details) -> Job | None:
        link = item.link.text
        title = item.title.text
        description = item.description.text.lower()
        location = description.split("\n")[0]  # First line contains location

        if not self.validate_keywords_and_region(
            link=link,
            title=title,
            description=description,
            region=location,
        ):
            return

        salary = None
        # Try different salary patterns
        if salary_matches := SALARY_RANGE_REGEX.search(description):
            salary = salary_matches.group(1)
        elif rate_matches := RATE_REGEX.search(description):
            rate = int(rate_matches.group(1))
            # Convert hourly rate to annual (assuming 40 hours/week, 52 weeks/year)
            salary = str(rate * 40 * 52)
        elif hourly_matches := HOURLY_RATE_REGEX.search(description):
            min_rate, max_rate = map(int, hourly_matches.groups())
            # Use the higher rate for salary validation
            salary = str(max_rate * 40 * 52)
        elif salary_matches := SALARY_REGEX.search(description):
            salary = salary_matches.group()

        validated_salary = self.validate_salary(link=link, salary=salary)
        if not validated_salary:
            return

        posted_on = None
        if posted_on_str := job_details.get(link, {}).get("posted_on"):
            posted_on = datetime.fromisoformat(posted_on_str)

        return Job(
            title=title,
            salary=validated_salary,
            link=link,
            location=location,
            posted_on=posted_on,
        )
