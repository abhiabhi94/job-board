from decimal import Decimal, InvalidOperation
import json

import openai
import httpx

from job_board.base import JobListing
from job_board import config
from job_board.logger import logger


class BasePortal:
    portal_name: str
    url: str
    api_data_format: str = "json"

    region_mapping: dict[str, set[str]]

    def __init__(self):
        self.openai_client = openai.Client(
            api_key=config.OPENAI_API_KEY, timeout=httpx.Timeout(30)
        )

    def get_jobs_to_notify(self) -> list[JobListing]:
        raise NotImplementedError()

    def validate_keywords_and_region(
        self, *, link, title, description, region, tags=None
    ) -> bool:
        logger.debug(f"Validating keywords and region for {link}")

        title = title.lower()
        description = description.lower()
        region = region.lower()
        if not tags:
            tags = []
        tags = [tag.lower() for tag in tags]
        keywords = config.KEYWORDS

        keyword_matches = (
            keywords.intersection(title.split())
            or keywords.intersection(description.split())
            or keywords.intersection(tags)
        )

        if not keyword_matches:
            logger.debug(f"No keyword matches found for {link}")
            return False

        region_matches = self.region_mapping[config.REGION].intersection(region.split())
        if not region_matches:
            logger.debug(f"No region matches found for {link}")
            return False

        return True

    def validate_salary(self, *, link: str, salary: str) -> str | None:
        logger.debug(f"Looking for salary information in {link}")

        if salary is None:
            # no salary information, should we still consider this relevant ???
            logger.debug(f"No salary information found for {link}")
            return

        salary = salary.replace("$", "").replace(",", "")
        try:
            salary = Decimal(str(salary))
        except InvalidOperation:
            logger.debug(f"Invalid salary {salary} for {link}")
            return

        if salary < config.SALARY:
            logger.debug(f"Salary {salary} for {link} is less than {config.SALARY}")
            return

        return salary

    def process_jobs_with_llm(self, job_data):
        developer_prompt = f"""
        You are a job extraction and filtering assistant.
        You will be given raw data containing job listings (HTML, JSON, or XML).
        First extract and normalise relevant job details from the raw data.

        When extracting, consider the following attributes:
        - Title
        - Description(if available)
        - Tags (if available)
        - Salary
        - Location
        - Posted Date
            - Convert the posted date to a format in UTC,
              ISO 8601 date-time string (YYYY-MM-DDTHH:MM:SSZ).
                - If the provided date is like "1 day ago", "5 days ago",
                  convert it to the actual date.
        - Link (Application URL)

        Keeping in mind the key names might be different but they will
        be similar to the above attributes. Consider equivalent attributes
        like: "Location" and "region", "Salary" and "compensation",
        "Posted Date" and "publication_date", etc.

        Now, filter the jobs based on the following criteria:
        - Job title or description or tags : {config.KEYWORDS}
        - Regions that match the equivalent of: {config.REGION}
        - Minimum Salary: {config.SALARY} {config.CURRENCY_SALARY}

        Your response will be a list of matched job listings,
        each containing the following attributes:

        ```JobListing.__annotations__```

        The response format should be JSON.
        """
        user_prompt = f"""
        Raw Data is in {self.api_data_format.upper()}.

        Raw Data:
        ```
        {job_data}
        ```
        """

        response = self.openai_client.chat.completions.create(
            model=config.OPEN_AI_MODEL,
            messages=[
                {"role": "developer", "content": developer_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        openai_response = response.choices[0].message.content

        logger.debug(f"OpenAI response: {openai_response}")
        if openai_response:
            return [JobListing(**job) for job in json.loads(openai_response)]
        else:
            return []
