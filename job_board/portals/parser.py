import json
import re
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal
from functools import cached_property
from typing import NamedTuple

import httpx
import pycountry
from babel.numbers import format_compact_currency
from lxml import etree
from lxml import html
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from requests.structures import CaseInsensitiveDict

from job_board import config
from job_board.logger import logger
from job_board.utils import get_currency_from_symbol
from job_board.utils import get_exchange_rate
from job_board.utils import get_iso2
from job_board.utils import get_openai_schema
from job_board.utils import http_client
from job_board.utils import retry_on_http_errors


OPENAI_RESPONSES_API_URL = "https://api.openai.com/v1/responses"

SALARY_AMOUNT_REGEX = re.compile(
    r"""
    (?P<currency_symbol>[^\w\s\d,.-]*)           # Currency symbol(s)
    (?P<amount>\d+(?:,\d{3})*(?:\.\d+)?)  # Salary number with optional decimal
    (?P<multiplier>[klmb]?)               # Suffix (k/l/m/b)
    (?:\s+(?P<currency_code>[a-z]{2,4}))?        # Currency code at end
    """,
    re.VERBOSE | re.IGNORECASE,
)
SALARY_RANGE_REGEX = re.compile(
    r"""
    (?P<currency_symbol>[^\w\s\d,.-]*)           # Currency symbol(s)
    (?P<min_amount>\d+(?:,\d{3})*(?:\.\d+)?)     # First number with optional decimal
    (?P<min_amount_multiplier>[klmb]?)           # First suffix
    \s*[–\-]\s*                                  # Required range separator
    (?P<currency_symbol2>[^\w\s\d,.-]*)          # Second currency symbol
    (?P<max_amount>\d+(?:,\d{3})*(?:\.\d+)?)     # Second number with optional decimal
    (?P<max_amount_multiplier>[klmb]?)           # Second suffix
    (?:\s+(?P<currency_code>[a-z]{2,4}))?        # Currency code at end
    """,
    re.VERBOSE | re.IGNORECASE,
)

STRING_LITERAL_REGEX = re.compile(r'"([^"\\\\]*(\\\\.[^"\\\\]*)*)"')

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
        "React.js": "react",
        "ReactJS": "react",
        "React JS": "react",
    }
)


class InvalidSalary(Exception):
    pass


class Money(NamedTuple):
    currency: str | None
    amount: Decimal | None


class SalaryRange(NamedTuple):
    min_salary: Money
    max_salary: Money


class Job(BaseModel):
    id: int | None = None
    title: str
    description: str | None = None
    link: str
    min_salary: Decimal | None = None
    max_salary: Decimal | None = None
    posted_on: datetime | None = None
    tags: list[str] | None = Field(default_factory=list)
    is_remote: bool = False
    locations: list[str] | None = Field(default_factory=list)
    payload: str | None = None
    extra_info: str | None = None
    portal_name: str | None = None
    company_name: str | None = None

    model_config = ConfigDict(frozen=True)

    @property
    def salary_range(self) -> str:
        min_formatted = self.min_salary and format_compact_currency(
            self.min_salary,
            currency=config.DEFAULT_CURRENCY,
            locale=config.DEFAULT_LOCALE,
        )
        max_formatted = self.max_salary and format_compact_currency(
            self.max_salary,
            currency=config.DEFAULT_CURRENCY,
            locale=config.DEFAULT_LOCALE,
            fraction_digits=config.DEFAULT_CURRENCY_FRACTION_DIGITS,
        )
        if not min_formatted and not max_formatted:
            return ""

        if min_formatted == max_formatted:
            return min_formatted

        if min_formatted and max_formatted:
            return f"{min_formatted} - {max_formatted}"
        elif min_formatted:
            return f"{min_formatted} and above"

        return f"Up to {max_formatted}"


class JobParser:
    def __init__(self, *, item: object, api_data_format):
        self.item = item
        self.api_data_format = api_data_format

    @cached_property
    def extra_info(self) -> html.HtmlElement | None:
        return self.get_extra_info()

    def get_extra_info(self) -> html.HtmlElement | None:
        """Extracts extra information from the item."""
        raise NotImplementedError()

    def get_job(self) -> Job:
        link = self.get_link()
        posted_on = self.get_posted_on()
        title = self.get_title().strip()
        description = self.get_description().strip()
        company_name = self.get_company_name()
        if company_name is not None:
            company_name = company_name.strip()
        tags = self._normalize_tags(self.get_tags())
        salary_range = self.get_salary_range()
        min_salary = salary_range.min_salary
        max_salary = salary_range.max_salary
        is_remote = self.get_is_remote()
        locations = self.get_locations()
        payload = self.get_payload()
        try:
            extra_info = self.extra_info
        except NotImplementedError:
            extra_info = None
        else:
            if extra_info is not None:
                extra_info = html.tostring(extra_info, encoding="unicode")

        return Job(
            link=link,
            title=title,
            description=description,
            tags=tags,
            posted_on=posted_on,
            min_salary=min_salary.amount,
            max_salary=max_salary.amount,
            is_remote=is_remote,
            locations=locations,
            payload=payload,
            extra_info=extra_info,
            company_name=company_name,
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

    def get_company_name(self) -> str | None:
        raise NotImplementedError()

    def _normalize_tags(self, tags: list[str]) -> list[str]:
        normalized_tags = []
        for tag in tags:
            _tag = tag.strip().lower()
            _tag = STANDARD_TAGS_MAPPING.get(_tag, _tag)
            normalized_tags.append(_tag)
        return normalized_tags

    def get_salary_range(self) -> SalaryRange:
        """Extracts the salary range from the item."""
        raise NotImplementedError()

    def get_is_remote(self) -> bool:
        """Checks if the job is remote."""
        raise NotImplementedError()

    def get_locations(self) -> list[str]:
        raise NotImplementedError()

    def get_payload(self) -> str:
        match self.api_data_format:
            case "json":
                return json.dumps(self.item)
            case "xml":
                return etree.tostring(self.item, encoding="unicode")
            case _:
                raise ValueError(f"Unsupported data format: {self.api_data_format}")

    def parse_salary(self, salary_str: str) -> Money:
        link = self.get_link()
        logger.debug(f"Getting salary information in {link}, {salary_str=}")

        currency = None
        amount = None
        if salary_str:
            try:
                salary = self.extract_salary(salary_str.strip())
            except InvalidSalary as exc:
                logger.exception(exc, stack_info=True)
            else:
                currency = salary.currency
                amount = salary.amount

        return Money(
            currency=currency,
            amount=amount,
        )

    def parse_salary_range(self, compensation: str | None) -> SalaryRange:
        try:
            salary_range = self.extract_salary_range(compensation)
        except InvalidSalary:
            min_salary = Money(currency=None, amount=None)
            max_salary = Money(currency=None, amount=None)
        else:
            min_salary = salary_range.min_salary
            max_salary = salary_range.max_salary

        return SalaryRange(
            min_salary=Money(
                currency=config.DEFAULT_CURRENCY,
                amount=self.get_amount_in_default_currency(
                    min_salary.amount, min_salary.currency
                ),
            ),
            max_salary=Money(
                currency=config.DEFAULT_CURRENCY,
                amount=self.get_amount_in_default_currency(
                    max_salary.amount, max_salary.currency
                ),
            ),
        )

    def extract_salary_range(self, compensation: str | None) -> SalaryRange:
        compensation = compensation or ""
        salary_info, _, _ = compensation.partition("•")
        salary_info = salary_info.strip()
        link = self.get_link()
        if not salary_info:
            raise InvalidSalary(f"{link=} has no salary info.")

        matches = SALARY_RANGE_REGEX.search(salary_info)
        if not matches:
            raise InvalidSalary(f"{link=} has unsupported salary format: {salary_info}")

        groups = matches.groupdict()
        currency_symbol = groups["currency_symbol"]
        min_amount = groups["min_amount"]
        min_amount_multiplier = groups["min_amount_multiplier"]
        max_amount = groups["max_amount"]
        max_amount_multiplier = groups["max_amount_multiplier"]
        currency_code = groups["currency_code"]

        currency = None
        if not currency_code and not currency_symbol:
            if min_amount.isnumeric() and max_amount.isnumeric():
                currency = config.DEFAULT_CURRENCY
        else:
            currency = self.get_currency(currency_code, currency_symbol)

        if not currency:
            link = self.get_link()
            raise InvalidSalary(
                f"{link=} has unsupported {currency_code=} or {currency_symbol=}."
            )

        min_salary_amount = self.convert_num(
            amount=min_amount, multiplier=min_amount_multiplier
        )
        max_salary_amount = self.convert_num(
            amount=max_amount, multiplier=max_amount_multiplier
        )

        return SalaryRange(
            min_salary=Money(currency=currency, amount=min_salary_amount),
            max_salary=Money(currency=currency, amount=max_salary_amount),
        )

    def extract_salary(self, salary_info: str) -> Money:
        link = self.get_link()
        if not salary_info:
            raise InvalidSalary(f"{link=} has no salary info.")

        matches = SALARY_AMOUNT_REGEX.search(salary_info.strip())
        if not matches:
            raise InvalidSalary(f"{link=} has unsupported salary format: {salary_info}")

        groups = matches.groupdict()
        currency_symbol = groups["currency_symbol"]
        amount = groups["amount"]
        multiplier = groups["multiplier"]
        currency_code = groups["currency_code"]
        currency = self.get_currency(currency_code, currency_symbol)
        if not currency:
            if amount.isnumeric():
                currency = config.DEFAULT_CURRENCY
            else:
                raise InvalidSalary(
                    f"{link=} has unsupported {currency_code=} or {currency_symbol=}."
                )

        amount = self.convert_num(amount=amount, multiplier=multiplier)
        return Money(currency=currency, amount=amount)

    @staticmethod
    def convert_num(amount: str | Decimal, multiplier: str | None) -> Decimal:
        amount = amount.replace(",", "")
        amount = Decimal(str(amount))
        if not multiplier:
            multiplier = ""

        match multiplier.lower():
            case "k":
                amount *= 1_000
            case "m":
                amount *= 1_000_000
            case "b":
                amount *= 1_000_000_000
            case "l":
                amount *= 100_000
            case "":
                pass
        return amount

    @staticmethod
    def get_currency(code: str | None, symbol: str | None) -> str | None:
        currency = None
        if code:
            currency_obj = pycountry.currencies.get(alpha_3=code)
            if currency_obj:
                currency = currency_obj.alpha_3
        elif symbol:
            currency = get_currency_from_symbol(symbol)
        return currency

    def get_amount_in_default_currency(
        self, amount: Decimal | None, currency=None
    ) -> Decimal:
        if not amount:
            return None

        currency = currency or self.get_currency()
        exchange_rate = get_exchange_rate(
            from_currency=currency,
            to_currency=config.DEFAULT_CURRENCY,
            exchange_date=self.get_posted_on(),
        )
        link = self.get_link()
        if not exchange_rate:
            logger.warning(f"No exchange rate found for {currency=}, {link=}")
            exchange_rate = Decimal("1")

        amount = (amount / exchange_rate).quantize(Decimal("0.01"))

        return amount

    @classmethod
    def parse_locations_from_json_ld(
        cls, document: None | html.HtmlElement
    ) -> list[str]:
        data = cls.parse_json_ld(document)
        if not data:
            return []

        locations = []
        if locations_info := data.get("applicantLocationRequirements"):
            if isinstance(locations_info, dict):
                # for single location, convert it to a list
                locations_info = [locations_info]

            for location_info in locations_info:
                name = location_info["name"]
                if iso_code := get_iso2(name):
                    locations.append(iso_code)

        return locations

    @classmethod
    def parse_json_ld(cls, document: None | html.HtmlElement) -> dict | None:
        if document is None:
            return None

        try:
            (script,) = document.xpath('//script[@type="application/ld+json"]')
        except ValueError:
            return None

        json_ld = json.loads(cls._fix_json_newlines(script.text_content()))
        return json_ld

    @staticmethod
    def _fix_json_newlines(text: str) -> str:
        """
        Fix newlines in JSON strings using regex.
        Mainly used by WeWorkRemotely to handle newlines in JSON-LD.
        Their JSON-LD sometimes has newlines that break parsing.
        """

        def escape_newlines(match):
            return match.group(0).replace("\n", "\\n").replace("\r", "\\r")

        return STRING_LITERAL_REGEX.sub(escape_newlines, text)


@retry_on_http_errors(max_attempts=10, max_wait=5)
def extract_job_tags_using_llm(jobs: list[Job]) -> list[Job]:
    class JobTags(BaseModel):
        link: str
        tags: list[str]

    class JobsTags(BaseModel):
        jobs: list[JobTags]

    job_data = [job.model_dump() for job in jobs]
    if not job_data:
        return []

    input_links = [job.link for job in jobs]
    job_data_length = len(job_data)
    prompt = f"""
You are a job analysis system. You MUST process EXACTLY {job_data_length} job postings and return EXACTLY {job_data_length} results.

INPUT JOBS TO ANALYZE:
{json.dumps(job_data, indent=2)}

CRITICAL REQUIREMENTS:
1. Process ALL {job_data_length} jobs - missing even one job is a FAILURE
2. Use ONLY the exact links provided above - DO NOT create, modify, or hallucinate any links
3. Your response must have EXACTLY {job_data_length} results with these EXACT links:
   {list(input_links)}
4. Extract MAXIMUM 5 tags per job (never exceed this limit)
5. Only include technical skills, programming languages, frameworks, and tools explicitly mentioned in the job description
6. Use standard industry terms in lowercase
7. For non-technical jobs (HR, sales, marketing, management, etc.), return exactly: ["non-tech"]
8. Do not assume or infer technologies not explicitly mentioned
"""  # noqa: E501

    schema = get_openai_schema(JobsTags)
    data = {
        "model": config.OPENAI_MODEL,
        "input": [
            {
                "role": "system",
                "content": (
                    "You are an expert at structured data extraction. "
                    "You will extract technical tags from job postings."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": JobsTags.__name__,
                "schema": schema,
                "strict": True,
            }
        },
        "temperature": 0,
    }

    with http_client() as client:
        # https://platform.openai.com/docs/guides/structured-outputs?api-mode=responses&lang=curl&example=structured-data#examples  # noqa: E501
        response = client.post(
            OPENAI_RESPONSES_API_URL,
            timeout=httpx.Timeout(
                config.DEFAULT_HTTP_TIMEOUT, read=config.OPENAI_READ_TIMEOUT
            ),
            headers={
                "Authorization": f"Bearer {config.OPENAI_API_KEY}",
            },
            json=data,
        )

    result = response.json()
    logger.debug(f"OpenAI response ID: {result['id']}")
    text = json.loads(result["output"][0]["content"][0]["text"])
    job_link_map = {j.link: j for j in jobs}

    job_with_tags = []
    for job in text["jobs"]:
        job_without_tag = job_link_map[job["link"]]
        job_with_tags.append(
            job_without_tag.model_copy(
                update={"tags": job["tags"]},
                deep=True,
            )
        )
    return job_with_tags
