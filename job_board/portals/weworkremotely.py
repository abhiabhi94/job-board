import re
from datetime import datetime

from lxml import html
from lxml import objectify

from job_board.portals.base import BasePortal
from job_board.utils import make_scrapfly_request

# matches "60,000" or "60,000,000"
SALARY_REGEX = re.compile(r"\b\d{2,}(?:,\d{3})+\b")


class WeWorkRemotely(BasePortal):
    portal_name = "weworkremotely"
    url = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
    api_data_format = "xml"

    def make_request(self) -> str:
        return make_scrapfly_request(self.url)

    def get_items(self, response: bytes) -> list[objectify.ObjectifiedElement]:
        root = objectify.fromstring(response.encode())
        return root.channel.item

    def get_link(self, item):
        return item.link.text

    def get_title(self, item):
        return item.title.text

    def get_description(self, item):
        return item.description.text

    def get_salary(self, item):
        link = self.get_link(item)
        details = make_scrapfly_request(link)
        root = html.fromstring(details)
        salary_elements = root.xpath(
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'salary')]"  # noqa: E501
        )
        salary_info = None
        salary = None
        for element in salary_elements:
            text_content = element.text_content().lower().strip()
            salary_matches = SALARY_REGEX.search(text_content)
            if salary_matches:
                salary_info = salary_matches.group()
                break

            salary = self.parse_salary(link=link, salary_str=salary_info)

        return salary

    def get_posted_on(self, item):
        date_string = item.pubDate.text
        return datetime.strptime(date_string, "%a, %d %b %Y %H:%M:%S %z")

    def is_remote(self, item):
        region = item.region.text
        return region.lower() == "anywhere in the world"

    # TODO: extract tags and location, right now this
    # information is not very structured, and is present
    # in the details page.
