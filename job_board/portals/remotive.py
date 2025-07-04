from datetime import datetime
from datetime import timezone

from lxml import html

from job_board.portals.base import BasePortal
from job_board.portals.parser import JobParser
from job_board.utils import httpx_client

RELEVANT_KEYS = {
    "title",
    "url",
    "salary",
    "tags",
    "candidate_required_location",
    "publication_date",
}

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


class Parser(JobParser):
    def get_link(self):
        return self.item["url"]

    def get_title(self):
        return self.item["title"]

    def get_description(self):
        return html.fromstring(self.item["description"]).text_content()

    def get_posted_on(self) -> datetime:
        return (
            datetime.strptime(self.item["publication_date"], DATE_FORMAT)
        ).astimezone(timezone.utc)

    def get_salary_range(self):
        return self.parse_salary_range(compensation=self.item.get("salary"))

    def get_tags(self):
        return self.item["tags"]

    def get_locations(self):
        return [self.item["candidate_required_location"]]

    def get_is_remote(self):
        return self.item["candidate_required_location"].lower() == "worldwide"


class Remotive(BasePortal):
    """Docs: https://github.com/remotive-com/remote-jobs-api"""

    portal_name = "remotive"
    url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=500"
    api_data_format = "json"
    parser_class = Parser

    def make_request(self):
        with httpx_client() as client:
            response = client.get(self.url)

        return response.json()

    def get_items(self, data) -> list[dict]:
        return data["jobs"]
