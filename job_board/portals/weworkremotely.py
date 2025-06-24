import re
from datetime import datetime

from lxml import html
from lxml import objectify

from job_board.portals.base import BasePortal
from job_board.portals.parser import JobParser
from job_board.utils import make_scrapfly_request
from job_board.utils import retry_on_http_errors

# matches "60,000" or "60,000,000"
SALARY_REGEX = re.compile(r"\b\d{2,}(?:,\d{3})+\b")


class Parser(JobParser):
    def get_link(self):
        return self.item.link.text

    def get_title(self):
        return self.item.title.text

    def get_description(self):
        return self.item.description.text

    def get_extra_info(self):
        return html.fromstring(self._get_extra_info())

    @retry_on_http_errors()
    def _get_extra_info(self):
        link = self.get_link()
        return make_scrapfly_request(link, timeout=100)

    def get_salary(self):
        root = self.extra_info
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

            salary = self.parse_salary(salary_str=salary_info)

        return salary

    def get_posted_on(self):
        date_string = self.item.pubDate.text
        return datetime.strptime(date_string, "%a, %d %b %Y %H:%M:%S %z")

    def get_is_remote(self):
        region = self.item.region.text
        return region.lower() == "anywhere in the world"

    def get_tags(self) -> list[str]:
        root = self.extra_info
        skill_elements = root.xpath(
            '//li[contains(text(), "Skills")]//span[@class="box box--multi box--blue"]'
        )
        return [element.text_content().strip() for element in skill_elements]


class WeWorkRemotely(BasePortal):
    portal_name = "weworkremotely"
    url = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
    api_data_format = "xml"
    parser_class = Parser

    @retry_on_http_errors()
    def make_request(self) -> str:
        return make_scrapfly_request(self.url, timeout=100)

    def get_items(self, response: bytes) -> list[objectify.ObjectifiedElement]:
        root = objectify.fromstring(response.encode())
        return root.channel.item
