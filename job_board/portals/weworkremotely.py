import re

from lxml import html
from lxml import objectify

from job_board.base import Job
from job_board.logger import logger
from job_board.portals.base import BasePortal
from job_board.utils import make_scrapfly_request
from job_board.utils import parse_relative_time

# matches "60,000" or "60,000,000"
SALARY_REGEX = re.compile(r"\b\d{2,}(?:,\d{3})+\b")
# matches "posted 5 days ago" or "posted 5 hours ago"
POSTED_ON_REGEX = re.compile(
    (
        r"\bposted\s(\d+\s+day[s]?\s+ago)\b"
        r"|\bposted\s(\d+\s+hour[s]?\s+ago)\b"
        r"|\bposted\s(\d+\s+minute[s]?\s+ago)\b"
    ),
    re.IGNORECASE,
)
TIME_FILTERS = (
    "day ago",
    "days ago",
    "hour ago",
    "hours ago",
    "minute ago",
    "minutes ago",
)
POSTED_ON_XPATH = (
    "//*[" + " or ".join(f"contains(text(), '{t}')" for t in TIME_FILTERS) + "]"
)


class WeWorkRemotely(BasePortal):
    portal_name = "weworkremotely"
    url = "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss"
    api_data_format = "xml"

    region_mapping = {
        "remote": {
            "anywhere",
        },
    }

    def get_jobs(self) -> list[Job]:
        response = make_scrapfly_request(self.url)
        return self.filter_jobs(response)

    def filter_jobs(self, data):
        root = objectify.fromstring(data.encode())
        links_to_look = []
        for item in root.channel.item:
            link = item.link.text
            if self.validate_keywords_and_region(
                link=link,
                title=item.title.text,
                description=item.description.text,
                region=item.region.text,
            ):
                links_to_look.append(link)

        logger.debug(f"Found {links_to_look} links to look for salary information")
        job_listings_to_notify: list[Job] = []
        for link in links_to_look:
            if job_listing := self.filter_job(link):
                job_listings_to_notify.append(job_listing)
        return job_listings_to_notify

    def filter_job(self, link) -> Job | None:
        response = make_scrapfly_request(link)
        root = html.fromstring(response)
        salary_elements = root.xpath(
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'salary')]"  # noqa: E501
        )
        salary = None
        for element in salary_elements:
            text_content = element.text_content().lower().strip()
            salary_matches = SALARY_REGEX.search(text_content)
            if salary_matches:
                salary = salary_matches.group()
                break

        validated_salary = self.validate_salary(link=link, salary=salary)
        if not validated_salary:
            return

        posted_on_str = None
        posted_on_elements = root.xpath(POSTED_ON_XPATH)

        for element in posted_on_elements:
            text_content = element.text_content().lower().strip()
            posted_on_matches = POSTED_ON_REGEX.search(text_content)
            if posted_on_matches:
                posted_on_str = (
                    posted_on_matches.group(1)
                    # in case of hours, the second group will be matched
                    or posted_on_matches.group(2)
                    # in case of minutes, the third group will be matched
                    or posted_on_matches.group(3)
                )
                break

        posted_on = parse_relative_time(posted_on_str)

        return Job(
            title=root.findtext(".//title").strip(),
            salary=validated_salary,
            link=link,
            posted_on=posted_on,
        )
