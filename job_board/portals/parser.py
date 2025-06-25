import json
import re
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal
from decimal import InvalidOperation
from functools import cached_property

import humanize
import pycountry
from lxml import etree
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from requests.structures import CaseInsensitiveDict

from job_board import config
from job_board.logger import logger
from job_board.utils import get_currency_from_symbol
from job_board.utils import get_exchange_rate

# matches "60,000" or "60,000,000"
SALARY_REGEX = re.compile(r"\b\d{2,}(?:,\d{3})+\b")
# matches "Rate: up to $80" or "Rate: $80"
RATE_REGEX = re.compile(r"Rate:\s*(?:up to\s*)?\$(\d+)")
# matches "salary range for this position is $120,000 - $165,000"
SALARY_RANGE_REGEX = re.compile(r"salary range.*?\$(\d{2,}(?:,\d{3})+)")
# matches "45–70 USD per hour" or "45-70 USD per hour"
HOURLY_RATE_REGEX = re.compile(r"(\d+)[–-](\d+)\s*USD\s*per\s*hour")

CURRENCY_CODE_REGEX = re.compile(r"([A-Z]{3})$", re.IGNORECASE)


STANDARD_TAGS_MAPPING = CaseInsensitiveDict()
STANDARD_TAGS_MAPPING.update(
    {
        "Back end": "backend",
        "Back-end": "backend",
        "front end": "frontend",
        "Front-end": "frontend",
        "Fullstack": "full stack",
        "Full-stack": "full stack",
        "DataScience": "data science",
        "Node js": "node.js",
        "Nodejs": "node.js",
    }
)


class InvalidSalary(Exception):
    pass


class Job(BaseModel):
    title: str
    description: str | None = None
    link: str
    salary: Decimal | None = None
    posted_on: datetime | None = None
    tags: list[str] | None = Field(default_factory=list)
    is_remote: bool = False
    locations: list[str] | None = Field(default_factory=list)
    payload: str | None = None

    model_config = ConfigDict(frozen=True)

    def __str__(self):
        model_dump = self.model_dump()
        max_key_length = (
            max(len(key) for key in model_dump) + 2  # Padding for alignment
        )

        formatted_values = []
        for key, value in model_dump.items():
            if key == "payload":
                continue
            if value is None:
                value = "N/A"

            # Convert snake_case to Title Case
            key_repr = key.replace("_", " ").title()
            if isinstance(value, datetime):
                value = (humanize.naturaltime(value)).capitalize()
            elif isinstance(value, bool):
                value = "Yes" if value else "No"
            elif isinstance(value, (Decimal, int, float)):
                value = f"{value:,.2f}"
            elif isinstance(value, list):
                value = ", ".join(value)

            formatted_values.append(f"{key_repr.ljust(max_key_length)}: {value}")

        return "\n".join(formatted_values)


class JobParser:
    def __init__(self, *, item: object, portal_name, api_data_format):
        self.item = item
        self.api_data_format = api_data_format
        self.portal_name = portal_name

    @cached_property
    def extra_info(self):
        return self.get_extra_info()

    def get_extra_info(self):
        """Extracts extra information from the item."""
        raise NotImplementedError()

    def get_job(self) -> Job | None:
        if not self.validate_recency():
            link = self.get_link()
            posted_on = self.get_posted_on()
            logger.info(f"{link=} {posted_on=} is too old, skipping.")
            return None

        return self._get_job()

    def _get_job(self) -> Job:
        link = self.get_link()
        posted_on = self.get_posted_on()
        title = self.get_title().strip()
        description = self.get_description().strip()
        tags = self._normalize_tags(self.get_tags())
        salary = self.get_salary()
        is_remote = self.get_is_remote()
        locations = self.get_locations()
        payload = self.get_payload()

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

    def validate_recency(self) -> bool:
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(
            days=config.JOB_AGE_LIMIT_DAYS
        )
        posted_on = self.get_posted_on()
        if posted_on and posted_on < cutoff_date:
            return False
        return True

    def get_link(self) -> str:
        """Extracts the link from the item."""
        raise NotImplementedError()

    def get_title(self) -> str:
        """Extracts the title from the item."""
        raise NotImplementedError()

    def get_description(self) -> str:
        """Extracts the description from the item."""
        raise NotImplementedError()

    def get_posted_on(self) -> datetime:
        """Extracts the posted date from the item."""
        raise NotImplementedError()

    def get_tags(self) -> list[str]:
        """Extracts the tags from the item."""
        raise NotImplementedError()

    def _normalize_tags(self, tags: list[str]) -> list[str]:
        normalized_tags = []
        for tag in tags:
            _tag = tag.strip().lower()
            _tag = STANDARD_TAGS_MAPPING.get(_tag, _tag)
            normalized_tags.append(_tag)
        return normalized_tags

    def get_salary(self) -> str | None:
        """Extracts the salary from the item."""
        raise NotImplementedError()

    def get_is_remote(self) -> bool:
        """Checks if the job is remote."""
        raise NotImplementedError()

    def get_locations(self) -> list[str] | None:
        return []

    def get_payload(self) -> str:
        match self.api_data_format:
            case "json":
                return json.dumps(self.item)
            case "xml":
                return etree.tostring(self.item, encoding="unicode")
            case _:
                raise ValueError(f"Unsupported data format: {self.api_data_format}")

    def parse_salary(self, *, salary_str: str) -> Decimal | None:
        link = self.get_link()
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
        compensation: str | None,
        range_separator: str = "-",
    ):
        if not compensation:
            return

        try:
            currency, salary = self.get_currency_and_salary(
                compensation=compensation,
                range_separator=range_separator,
            )
        except InvalidSalary as exc:
            logger.exception(str(exc), stack_info=True)
            return

        posted_on = self.get_posted_on()
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
        compensation: str,
        range_separator: str = "-",
    ) -> tuple[str, Decimal]:
        link = self.get_link()
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
