import json
from decimal import Decimal
from datetime import datetime, timezone

from scrapfly import ScrapflyClient, ScrapeConfig
from lxml import html

from job_board import config
from job_board.base import Job
from job_board.portals.base import BasePortal
from job_board.logger import job_rejected_logger, logger
from job_board.utils import (
    ExchangeRate,
    Currency,
)


class InvalidSalary(Exception):
    pass


class Wellfound(BasePortal):
    portal_name = "wellfound"
    # This url actually depends upon the keywords
    # Wellfound doesn't seem to provide tags that we can
    # use to filter the jobs
    # For now, we are just hardcoding the url for python
    url = "https://wellfound.com/role/r/python-developer"
    api_data_format = "html"

    def __init__(self):
        self.scrapfly_client = ScrapflyClient(
            key=config.SCRAPFLY_API_KEY,
            debug=config.LOG_LEVEL == "DEBUG",
        )

    def get_jobs(self):
        response = self.scrapfly_client.scrape(
            ScrapeConfig(
                url=self.url,
                # automatically handle captchas
                asp=True,
            )
        )
        result = response.scrape_result
        return self.filter_jobs(result)

    def filter_jobs(self, data) -> list[Job]:
        element = html.fromstring(data["content"])
        data_element = element.get_element_by_id("__NEXT_DATA__")
        all_data = json.loads(data_element.text)

        job_results = [
            v
            for k, v in (all_data["props"]["pageProps"]["apolloState"]["data"].items())
            if k.startswith("JobListingSearchResult:")
        ]

        jobs = []
        for job_result in job_results:
            if job := self.filter_job(job_result):
                jobs.append(job)
        return jobs

    def filter_job(self, job_result) -> Job | None:
        slug = job_result["slug"]
        job_id = job_result["id"]
        link = f"https://wellfound.com/jobs/{job_id}-{slug}"
        if not job_result["remote"]:
            job_rejected_logger.debug(f"Job {link} is not remote, skipping it.")
            return

        posted_on = datetime.fromtimestamp(job_result["liveStartAt"]).astimezone(
            timezone.utc
        )
        if not self.validate_recency(link=link, posted_on=posted_on):
            return

        title = job_result["title"]
        description = job_result["description"]

        if not self.validate_keywords_and_region(
            link=link,
            title=title,
            description=description,
        ):
            return

        compensation = job_result["compensation"]
        if not compensation:
            job_rejected_logger.debug(f"Job {link} has no compensation, skipping it.")
            return

        try:
            currency, salary = self.get_currency_and_salary(
                link=link,
                compensation=compensation,
            )
        except InvalidSalary as exc:
            logger.debug(str(exc))
            return

        salary_in_dollars = salary * ExchangeRate[currency.name].value
        if salary_in_dollars < config.SALARY:
            job_rejected_logger.debug(
                (
                    f"Job {link} has salary {salary_in_dollars} less than "
                    "{config.SALARY}, skipping it."
                )
            )
            return

        return Job(
            title=title,
            salary=salary_in_dollars,
            link=link,
            posted_on=posted_on,
        )

    def get_currency_and_salary(self, link: str, compensation: str):
        # compensation is in the format of:
        # - "$100,000 – $150,000 • 1.0% – 2.0%"
        # - "₹15L – ₹25L"
        _, _, salary_and_equity_info = compensation.partition("–")
        salary_info, _, _ = salary_and_equity_info.partition("•")
        salary_info = salary_info.strip()
        if not salary_info:
            raise InvalidSalary(f"Job {link} has no salary info, skipping it.")

        symbol = salary_info[0].lower()

        try:
            currency = Currency(symbol)
        except ValueError:
            raise ValueError(
                f"Job {link} has unsupported currency symbol {symbol}, skipping it."
            )

        last_char = salary_info[-1].lower()
        # remove currency and last character.
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
