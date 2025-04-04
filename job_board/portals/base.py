from decimal import Decimal, InvalidOperation
import re
from datetime import datetime, timedelta, timezone


from pydantic import BaseModel
import openai
import httpx

from job_board.base import Job
from job_board import config
from job_board.logger import (
    logger,
    job_rejected_logger,
)
from job_board.utils import (
    Currency,
    ExchangeRate,
)

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


# since openai doesn't support date time, we will need to
# convert the date time to a string
# also, openAI wants all fields to be required.
class JobOpenAI(Job):
    posted_on: str
    location: str


class JobsOpenAI(BaseModel):
    jobs: list[JobOpenAI]


class BasePortal:
    portal_name: str
    url: str
    api_data_format: str = "json"

    region_mapping: dict[str, set[str]] | None

    @classmethod
    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        PORTALS[cls.portal_name] = cls

    def __init__(self):
        self.openai_client = openai.Client(
            api_key=config.OPENAI_API_KEY, timeout=httpx.Timeout(30)
        )

    def get_jobs(self) -> list[Job]:
        """Fetch filtered jobs from the portal."""
        raise NotImplementedError()

    def filter_jobs(self, data) -> list[Job]:
        """Filters jobs from the data received from the portal."""
        raise NotImplementedError()

    def validate_keywords_and_region(
        self, *, link, title, description, region=None, tags=None
    ) -> bool:
        logger.debug(f"Validating keywords and region for {link}")

        title = title.lower()
        description = description.lower()
        if not tags:
            tags = []
        tags = [tag.lower() for tag in tags]
        keywords = set(config.KEYWORDS)

        keyword_matches = (
            keywords.intersection(title.split())
            or keywords.intersection(description.split())
            or keywords.intersection(tags)
        )

        if not keyword_matches:
            job_rejected_logger.debug(f"No keyword matches found for {link}")
            return False

        if region:
            region = region.lower()
            region_matches = self.region_mapping[config.REGION].intersection(
                region.split()
            )
            if not region_matches:
                job_rejected_logger.debug(f"No region matches found for {link}")
                return False

        return True

    def validate_salary_range(
        self,
        link: str,
        compensation: str | None,
        range_separator: str = "-",
    ):
        if not compensation:
            job_rejected_logger.debug(f"Job {link} has no salary.")
            return

        try:
            currency, salary = self.get_currency_and_salary(
                link=link,
                compensation=compensation,
                range_separator=range_separator,
            )
        except InvalidSalary as exc:
            logger.debug(str(exc))
            return

        salary_in_dollars = salary * ExchangeRate[currency.name].value
        if salary_in_dollars < config.SALARY:
            job_rejected_logger.debug(
                (
                    f"Salary {salary_in_dollars} for {link} is less than "
                    f"{config.SALARY:,}"
                )
            )
            return

        return salary_in_dollars

    def get_currency_and_salary(
        self,
        link: str,
        compensation: str,
        range_separator: str = "-",
    ) -> tuple[Currency, Decimal]:
        # compensation is in the format of:
        # - "$100,000 – $150,000 • 1.0% – 2.0%"
        # - "₹15L – ₹25L"
        _, _, salary_and_equity_info = compensation.partition(range_separator)
        salary_info, _, _ = salary_and_equity_info.partition("•")
        salary_info = salary_info.strip()
        if not salary_info:
            raise InvalidSalary(f"Job {link} has no salary info.")

        # Extract possible currency code at the end
        if currency_match := CURRENCY_CODE_REGEX.search(salary_info):
            code = currency_match.group(1)
            salary_info = salary_info[: -len(code)].strip()
            try:
                currency = Currency[code.upper()]
            except KeyError:
                raise InvalidSalary(f"Job {link} has unsupported currency code {code}.")
        else:
            # fallback to the symbol if no code is found
            symbol = salary_info[0].lower()
            try:
                currency = Currency(symbol)
            except ValueError:
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

    def validate_salary(self, *, link: str, salary: str) -> str | None:
        logger.debug(f"Validating salary information in {link}")

        if salary is None:
            # no salary information, should we still consider this relevant ???
            job_rejected_logger.debug(f"No salary information found for {link}")
            return

        salary = salary.replace("$", "").replace(",", "")
        try:
            salary = Decimal(str(salary))
        except InvalidOperation:
            job_rejected_logger.debug(f"Invalid salary {salary} for {link}")
            return

        if salary < config.SALARY:
            job_rejected_logger.debug(
                f"Salary {salary} for {link} is less than {config.SALARY:,}"
            )
            return

        return salary

    def validate_recency(self, link: str, posted_on: datetime) -> bool:
        now = datetime.now(timezone.utc)
        if (now - posted_on) > timedelta(days=config.JOB_AGE_LIMIT_DAYS):
            job_rejected_logger.debug(f"Removing older job: {link}")
            return False
        return True

    def filter_jobs_with_llm(self, job_data) -> list[Job]:
        developer_prompt = f"""
        You are a job extraction and filtering assistant.
        You will be given raw data containing job listings (HTML, JSON, or XML).
        First extract and normalise relevant job details from the raw data.

        When extracting, consider the following attributes:
        - Title
        - Description(if available)
        - Tags (if available)
        - Salary
            - If a salary range is provided, use the **higher value** for
              comparison.
            - All salaries should be **converted within your response to
              {config.CURRENCY_SALARY} ** (do not assume conversion is
              done externally). Use the exchange rate as on 1st Jan 2025.
            - If the salary is mentioned as something like "30$ per hour",
              convert it to an annual salary, assuming a 40-hour workweek and
              52 weeks per year.
        - Location
        - Posted Date
            - Convert the posted date to a format in UTC,
              ISO 8601 date-time string (YYYY-MM-DDTHH:MM:SSZ).
                - If the provided date is like "1 day ago", "5 days ago",
                  convert it to the actual date.
        - Link (Application URL)

        Keep in mind the key names might be different but they will
        be similar to the above attributes.

        Consider these attributes as equivalent:
        - Location
            - region,
            - candidate_required_location,
            - location

        - Salary
            - compensation

        - Posted Date
            - publication_date

        The above list for considering attributes as equivalent
        is not exhaustive, and you might need to consider other
        attributes that may point to the same information as the
        one to be used for filtering and extracting.

        Filtering parameters:
        - Minimum Salary: {config.SALARY} {config.CURRENCY_SALARY}
        - Keywords: {config.KEYWORDS}
        - Region: {config.REGION}
        - Posted Date: {config.JOB_AGE_LIMIT_DAYS} days from today.

        Now, filter the jobs based on **all** the following criteria:

        - Job title or description or tags belong to one or more
          keywords : {config.KEYWORDS}

        - Regarding Region passed in the filtering parameter:
          - **STRICT MATCHING REQUIRED**: The job’s `location` field **MUST
            EXACTLY MATCH** "{config.REGION}" or an equivalent.

          - For example: If region is `"remote"`,
            **only accept** jobs where `location` is one of the following:
              - `"remote"`
              - `"fully remote"`
              - `"worldwide"`
              - `"work from anywhere"`
              - `"remote-first"`

          - **STRICTLY REJECT** jobs if `location` contains:
              - A specific country (e.g., `"USA"`, `"Canada"`, `"Germany"`)
              - A restricted region (e.g., `"Americas"`, `"EMEA"`, `"LATAM"`,
                `"APAC"`)
              - A hybrid/partial remote requirement (e.g., `"Remote USA"`,
                `"Remote but must be in Europe"`)

          - If region is a specific place (e.g., `"Europe"`):
              - **ONLY** accept listings where `location == "Europe"` or
                `"Remote Europe"`.
              - **STRICTLY REJECT** jobs mentioning **other regions** (e.g.,
                `"Americas"`, `"APAC"`, `"LATAM"`, `"USA"`).

          - **Final Check:**
              - **Before returning results**, iterate over all extracted jobs.
              - **REMOVE** any job where `location` does not exactly match
                "{config.REGION}".
              - The final output **MUST NOT** contain any job with an
                incorrect `location`.

            - **Examples of jobs that must be rejected before output:**
                ❌ `"USA"`
                ❌ `"USA only"`
                ❌ `"Canada"`
                ❌ `"Remote, USA only"`
                ❌ `"Remote but must be in Americas"`
                ❌ `"Americas, EMEA"`


        - Regarding salary:
            - Minimum Salary should be: {config.SALARY} {config.CURRENCY_SALARY}
            - If no salary is provided as a **valid number**, exclude the job
              listing.
            - If the salary is described as **"competitive"**, **"negotiable"**, or
              **"based on experience"**, assume it's below the minimum salary and
              **EXCLUDE IT**.
            - Ensure all salaries are converted to {config.CURRENCY_SALARY}.

        Your response will be a list of matched job listings.
        """
        user_prompt = f"""
        Raw Data format: `{self.api_data_format.upper()}`.

        Raw Data:
        ```
        {job_data}
        ```
        """

        response = self.openai_client.beta.chat.completions.parse(
            model=config.OPEN_AI_MODEL,
            messages=[
                {"role": "developer", "content": developer_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=JobsOpenAI,
        )
        openai_response = response.choices[0].message.parsed

        logger.debug(f"OpenAI response: {openai_response}")
        if openai_response:
            return [
                # the conversion is required since the OpenAI doesn't accept
                # datetime format, and we need to convert it to our native
                # pydantic model, so that the rest of the code works in a
                # consistent way.
                Job(**job.model_dump())
                for job in openai_response.jobs
            ]
        else:
            return []
