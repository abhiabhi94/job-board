from datetime import datetime
from datetime import timezone

from lxml import html

from job_board.portals.base import BasePortal
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


class Remotive(BasePortal):
    """Docs: https://github.com/remotive-com/remote-jobs-api"""

    portal_name = "remotive"
    url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=500"
    api_data_format = "json"

    def make_request(self):
        with httpx_client() as client:
            response = client.get(self.url)

        return response.json()

    def get_items(self, data) -> list[dict]:
        return data["jobs"]

    def get_link(self, item):
        return item["url"]

    def get_title(self, item):
        return item["title"]

    def get_description(self, item):
        return html.fromstring(item["description"]).text_content()

    def get_posted_on(self, job_data: dict[str, str]) -> datetime:
        return (
            datetime.strptime(job_data["publication_date"], DATE_FORMAT)
        ).astimezone(timezone.utc)

    def get_salary(self, item):
        link = self.get_link(item)
        return self.parse_salary_range(
            link=link,
            compensation=item.get("salary"),
        )

    def get_tags(self, item):
        return item["tags"]

    def get_locations(self, item):
        return [item["candidate_required_location"]]

    def is_remote(self, item):
        return item["candidate_required_location"].lower() == "worldwide"
