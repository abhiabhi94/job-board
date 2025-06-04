import json
import re
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal
from decimal import InvalidOperation

import pycountry
from lxml import etree

from job_board import config
from job_board.base import Job
from job_board.logger import logger
from job_board.utils import get_currency_from_symbol
from job_board.utils import get_exchange_rate

PORTALS = {}
# matches "60,000" or "60,000,000"
SALARY_REGEX = re.compile(r"\b\d{2,}(?:,\d{3})+\b")
# matches "Rate: up to $80" or "Rate: $80"
RATE_REGEX = re.compile(r"Rate:\s*(?:up to\s*)?\$(\d+)")
# matches "salary range for this position is $120,000 - $165,000"
SALARY_RANGE_REGEX = re.compile(r"salary range.*?\$(\d{2,}(?:,\d{3})+)")
# matches "45–70 USD per hour" or "45-70 USD per hour"
HOURLY_RATE_REGEX = re.compile(r"(\d+)[–-](\d+)\s*USD\s*per\s*hour")

CURRENCY_CODE_REGEX = re.compile(r"([A-Z]{3})$", re.IGNORECASE)


class InvalidSalary(Exception):
    pass


class BasePortal:
    portal_name: str
    url: str
    api_data_format: str

    @classmethod
    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        PORTALS[cls.portal_name] = cls

    def __init__(self, last_run_at: None | datetime = None):
        self.last_run_at = last_run_at

    def get_jobs(self) -> list[Job]:
        """Fetch filtered jobs from the portal."""
        response = self.make_request()
        items = self.get_items(response)
        jobs = []
        for item in items:
            if not self.validate_recency(item):
                continue
            job = self.get_job(item)
            jobs.append(job)
        return jobs

    def validate_recency(self, item: object) -> bool:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=365)
        posted_on = self.get_posted_on(item)
        if posted_on and posted_on < cutoff_date:
            link = self.get_link(item)
            logger.info(f"{link=} {posted_on=} is too old, skipping.")
            return False
        return True

    def get_job(self, item: object) -> Job | None:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=365)
        posted_on = self.get_posted_on(item)
        link = self.get_link(item)

        if posted_on and posted_on < cutoff_date:
            # no point in processing jobs that are too old
            logger.info(f"{link=} {posted_on=} is too old, skipping.")
            return None

        title = self.get_title(item)
        description = self.get_description(item)
        tags = self.get_tags(item)
        salary = self.get_salary(item)
        is_remote = self.is_remote(item)
        locations = self.get_locations(item)
        payload = self.get_payload(item)

        return Job(
            link=link,
            title=title,
            description=description,
            tags=tags,
            posted_on=posted_on,
            salary=salary,
            is_remote=is_remote,
            locations=locations,
            payload=payload,
        )

    def make_request(self) -> bytes | dict:
        """Makes a request to the portal and returns the response."""
        raise NotImplementedError()

    def get_items(self, response: bytes | dict) -> list[object]:
        """Parses the response and returns the items."""
        raise NotImplementedError()

    def get_link(self, item) -> str:
        """Extracts the link from the item."""
        raise NotImplementedError()

    def get_title(self, item) -> str:
        """Extracts the title from the item."""
        raise NotImplementedError()

    def get_description(self, item) -> str:
        """Extracts the description from the item."""
        raise NotImplementedError()

    def get_posted_on(self, item) -> datetime:
        """Extracts the posted date from the item."""
        raise NotImplementedError()

    def get_tags(self, item) -> list[str]:
        """Extracts the tags from the item."""
        return []

    def get_salary(self, item) -> str | None:
        """Extracts the salary from the item."""
        raise NotImplementedError()

    def is_remote(self, item) -> bool:
        """Checks if the job is remote."""
        raise NotImplementedError()

    def get_locations(self, item) -> list[str] | None:
        return []

    def get_payload(self, item: object) -> str:
        match self.api_data_format:
            case "json":
                return json.dumps(item)
            case "xml":
                return etree.tostring(item, encoding="unicode")
            case _:
                raise ValueError(f"Unsupported data format: {self.api_data_format}")

    def parse_salary(self, *, item: object, salary_str: str) -> Decimal | None:
        link = self.get_link(item)
        logger.debug(f"Getting salary information in {link}, {salary_str=}")

        if salary_str is None:
            return

        salary_str = salary_str.replace("$", "").replace(",", "")
        try:
            salary = Decimal(str(salary_str))
        except InvalidOperation:
            logger.info(f"Invalid salary {salary_str} for {link}")
            return

        return salary

    def parse_salary_range(
        self,
        item: object,
        compensation: str | None,
        range_separator: str = "-",
    ):
        if not compensation:
            return

        try:
            currency, salary = self.get_currency_and_salary(
                item=item,
                compensation=compensation,
                range_separator=range_separator,
            )
        except InvalidSalary as exc:
            logger.exception(str(exc), stack_info=True)
            return

        posted_on = self.get_posted_on(item)
        exchange_rate = get_exchange_rate(
            from_currency=currency,
            to_currency=config.DEFAULT_CURRENCY,
            exchange_date=posted_on,
        )
        if not exchange_rate:
            logger.warning(
                f"[{self.portal_name}]: No exchange rate found for "
                f"{currency=}, {posted_on=}"
            )
            exchange_rate = Decimal("1")

        return (salary / exchange_rate).quantize(Decimal("0.01"))

    def get_currency_and_salary(
        self,
        item: object,
        compensation: str,
        range_separator: str = "-",
    ) -> tuple[str, Decimal]:
        link = self.get_link(item)
        # compensation is in the format of:
        # - "$100,000 – $150,000 • 1.0% – 2.0%"
        # - "₹15L – ₹25L"
        # - "90000-120000"  -> remotive has this format
        _, _, salary_and_equity_info = compensation.partition(range_separator)
        salary_info, _, _ = salary_and_equity_info.partition("•")
        salary_info = salary_info.strip()
        if not salary_info:
            raise InvalidSalary(f"Job {link} has no salary info.")

        if salary_info.isnumeric():
            # this is probably salary without currency symbol
            # e.g. "100000 - 150000"
            # assume the currency is USD
            currency = config.DEFAULT_CURRENCY
            amount = Decimal(salary_info)
            return currency, amount

        # Extract possible currency code at the end
        if currency_match := CURRENCY_CODE_REGEX.search(salary_info):
            code = currency_match.group(1)
            salary_info = salary_info[: -len(code)].strip()
            currency = pycountry.currencies.get(alpha_3=code)
            if not currency:
                raise InvalidSalary(f"Job {link} has unsupported currency code {code}.")
            currency = currency.alpha_3
        else:
            # fallback to the symbol if no code is found
            symbol = salary_info[0].lower()
            currency = get_currency_from_symbol(symbol)
            if not currency:
                raise InvalidSalary(
                    f"Job {link} has unsupported currency symbol {symbol}."
                )

        last_char = salary_info[-1].lower()
        # remove symbol and last character.
        amount = salary_info[1:-1].replace(",", "")

        match last_char:
            case "k":
                salary = Decimal(amount) * 1_000
            case "m":
                salary = Decimal(amount) * 1_000_000
            case "b":
                salary = Decimal(amount) * 1_000_000_000
            case "l":
                salary = Decimal(amount) * 100_000
            case _:
                # this is probably an intern kind of job
                # where the salary is too less.
                raise InvalidSalary(f"Invalid salary info {salary_info} for {link}")

        return currency, salary
