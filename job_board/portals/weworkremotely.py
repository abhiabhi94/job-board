import re
from datetime import datetime
from datetime import timezone

from lxml import html
from lxml import objectify

from job_board import config
from job_board.portals.base import BasePortal
from job_board.portals.parser import JobParser
from job_board.portals.parser import Money
from job_board.portals.parser import SALARY_AMOUNT_REGEX
from job_board.portals.parser import SALARY_RANGE_REGEX
from job_board.portals.parser import SalaryRange
from job_board.utils import make_scrapfly_request
from job_board.utils import retry_on_http_errors

# matches "$100,000 or more USD", "100,000 or more", "$100k+", "₹15L or more" etc.
SALARY_OR_MORE_REGEX = re.compile(
    r"""
    (?P<currency_symbol>[^\w\s\d,.-]*)           # Currency symbol(s)
    (?P<amount>\d+(?:,\d{3})*)            # Salary number
    (?P<multiplier>[klmb]?)               # Suffix (k/l/m/b)
    (?:
        \s+or\s+more |                           # "or more" pattern
        \+                                       # Plus sign pattern
    )
    (?:\s+(?P<currency_code>[a-z]{2,4}))?        # Currency code at end
    """,
    re.VERBOSE | re.IGNORECASE,
)


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

    def get_salary_range(self) -> SalaryRange:
        root = self.extra_info
        salary_elements = root.xpath(
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'salary')]"  # noqa: E501
        )

        for element in salary_elements:
            text_content = element.text_content().strip()
            salary_range_match = SALARY_RANGE_REGEX.search(text_content)
            salary_or_more_match = SALARY_OR_MORE_REGEX.search(text_content)
            salary_matches = SALARY_AMOUNT_REGEX.search(text_content.lower())

            min_salary = Money(currency=None, amount=None)
            max_salary = Money(currency=None, amount=None)

            if salary_range_match:
                salary_range = self.parse_salary_range(
                    salary_range_match.group(),
                )
                min_salary = salary_range.min_salary
                max_salary = salary_range.max_salary

            elif salary_or_more_match:
                groups = salary_or_more_match.groupdict()
                amount = groups["amount"]
                multiplier = groups["multiplier"]
                min_amount = self.convert_num(amount=amount, multiplier=multiplier)
                currency = self.get_currency(
                    code=groups["currency_code"],
                    symbol=groups["currency_symbol"],
                )
                min_salary = Money(
                    currency=currency,
                    amount=min_amount,
                )

            elif salary_matches:
                salary_info = salary_matches.group()
                min_salary = self.parse_salary(salary_info)

            if not min_salary and not max_salary:
                continue

            min_amount_in_default_currency = self.get_amount_in_default_currency(
                amount=min_salary.amount, currency=min_salary.currency
            )
            max_amount_in_default_currency = self.get_amount_in_default_currency(
                amount=max_salary.amount, currency=max_salary.currency
            )
            return SalaryRange(
                min_salary=Money(
                    currency=config.DEFAULT_CURRENCY,
                    amount=min_amount_in_default_currency,
                ),
                max_salary=Money(
                    currency=config.DEFAULT_CURRENCY,
                    amount=max_amount_in_default_currency,
                ),
            )

        return SalaryRange(
            min_salary=Money(currency=None, amount=None),
            max_salary=Money(currency=None, amount=None),
        )

    def get_posted_on(self):
        date_string = self.item.pubDate.text
        return (datetime.strptime(date_string, "%a, %d %b %Y %H:%M:%S %z")).astimezone(
            timezone.utc
        )

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
