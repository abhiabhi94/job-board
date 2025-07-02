from datetime import datetime
from datetime import timezone

from lxml import html
from lxml import objectify

from job_board.portals.base import BasePortal
from job_board.portals.parser import Job
from job_board.portals.parser import JobParser
from job_board.portals.parser import Money
from job_board.portals.parser import SalaryRange
from job_board.utils import httpx_client


class Parser(JobParser):
    def get_link(self):
        return self.item.link.text

    def get_title(self):
        return self.item.title.text

    def get_description(self):
        return self.item.description.text

    def get_locations(self):
        description = self.get_description()
        # First line contains location
        location = description.split("\n")[0]
        return [location]

    def get_is_remote(self):
        locations = self.get_locations()
        locations = list(map(str.lower, locations))
        return (
            "remote" in locations
            or "worldwide" in locations
            or "anywhere" in locations
            or "global" in locations
        )

    def get_extra_info(self) -> html.HtmlElement:
        link = self.get_link()
        with httpx_client() as client:
            response = client.get(link)

        return html.fromstring(response.content)

    def get_posted_on(self):
        detail_page = self.extra_info
        try:
            (time_tag,) = detail_page.cssselect("time[datetime]")
        except ValueError:
            return None
        else:
            date_str = time_tag.get("datetime")
            return datetime.fromisoformat(date_str).astimezone(timezone.utc)

    def get_salary_range(self):
        # Most of the jobs don't have a salary
        # No direct way to get the salary from the rss feed
        return SalaryRange(
            min_salary=Money(currency=None, amount=None),
            max_salary=Money(currency=None, amount=None),
        )

    def get_tags(self):
        tags = ["python"]
        detail_page = self.extra_info
        try:
            (tag_element,) = detail_page.cssselect(".job-tags > .listing-job-type")
        except ValueError:
            job_tags = []
        else:
            job_tags = tag_element.text_content().strip().split(", ")

        return tags + job_tags


class PythonDotOrg(BasePortal):
    portal_name = "python_dot_org"
    base_url = "https://www.python.org"
    jobs_url = f"{base_url}/jobs/"
    url = f"{base_url}/jobs/feed/rss/"
    api_data_format = "xml"
    parser_class = Parser

    def make_request(self):
        with httpx_client() as client:
            response = client.get(self.url)

        return objectify.fromstring(response.content)

    def get_items(self, data) -> list[Job]:
        # The RSS feed contains a list of items
        # Each item is a job posting
        return data.channel.item
