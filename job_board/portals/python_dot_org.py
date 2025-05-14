from lxml import objectify

from job_board.base import Job
from job_board.portals.base import BasePortal
from job_board.utils import httpx_client


class PythonDotOrg(BasePortal):
    portal_name = "python_dot_org"
    base_url = "https://www.python.org"
    jobs_url = f"{base_url}/jobs/"
    url = f"{base_url}/jobs/feed/rss/"
    api_data_format = "xml"

    def make_request(self):
        with httpx_client() as client:
            response = client.get(self.url)

        return objectify.fromstring(response.content)

    def get_items(self, data) -> list[Job]:
        # The RSS feed contains a list of items
        # Each item is a job posting
        return data.channel.item

    def get_link(self, item):
        return item.link.text

    def get_title(self, item):
        return item.title.text

    def get_description(self, item):
        return item.description.text

    def get_locations(self, item):
        description = self.get_description(item)
        # First line contains location
        location = description.split("\n")[0]
        return [location]

    def is_remote(self, item):
        locations = self.get_locations(item)
        locations = list(map(str.lower, locations))
        return (
            "remote" in locations
            or "worldwide" in locations
            or "anywhere" in locations
            or "global" in locations
        )

    def get_posted_on(self, item):
        # There is no posted date in the rss feed
        # Can be fetched from the HTML description
        # on the job page, but too much work for now
        return

    def get_salary(self, item):
        # Most of the jobs don't have a salary
        # No direct way to get the salary from the rss feed
        return

    def get_tags(self, item):
        return ["python"]
