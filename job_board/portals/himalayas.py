from datetime import datetime, timezone, timedelta
from decimal import Decimal

from lxml import html
from tenacity import (
    Retrying,
    wait_exponential,
    retry_if_exception,
    stop_after_attempt,
)
import httpx

from job_board.portals.base import BasePortal
from job_board.base import Job
from job_board.utils import httpx_client, ExchangeRate
from job_board import config
from job_board.logger import job_rejected_logger, logger


def is_retryable(exception):
    if isinstance(exception, httpx.HTTPStatusError):
        status = exception.response.status_code
        return status == 429 or 500 <= status < 600
    return False


def before_sleep_logging(retry_state):
    logger.warning(
        (
            f"Retrying due to {retry_state.outcome.exception()!r}, "
            f"attempt: {retry_state.attempt_number}"
        )
    )


class Himalayas(BasePortal):
    """Docs: https://himalayas.app/api"""

    url = "https://himalayas.app/jobs/api"
    api_data_format = "json"
    portal_name = "himalayas"

    def get_jobs(self) -> list[Job]:
        if self.last_run_at:
            cutoff_date = self.last_run_at
        else:
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                config.JOB_AGE_LIMIT_DAYS
            )

        jobs_data = []
        jobs_fetched = 0
        with httpx_client() as client:
            while True:
                for attempt in Retrying(
                    stop=stop_after_attempt(5),
                    retry=retry_if_exception(is_retryable),
                    wait=wait_exponential(min=1, multiplier=1, max=5),
                    reraise=True,
                    before_sleep=before_sleep_logging,
                ):
                    with attempt:
                        response = client.get(
                            self.url,
                            params={"offset": jobs_fetched, "limit": 20},
                        ).json()

                total_jobs = response["totalCount"]
                job_data = response["jobs"]
                jobs_data.extend(job_data)
                jobs_fetched += len(job_data)
                logger.info(
                    (
                        f"[Himalayas]: Fetched {jobs_fetched} of {total_jobs} jobs, "
                        f"Remaining: {total_jobs - jobs_fetched}"
                    )
                )

                # no need to make any more requests if we have
                # already fetched all the jobs that were posted
                # after the last run or all jobs are too old.
                if all(cutoff_date > self.get_posted_on(j) for j in job_data):
                    logger.info(
                        f"[Himalayas]: No more jobs to fetch. "
                        f"{cutoff_date=}, {jobs_fetched=}"
                    )
                    break

                if jobs_fetched >= total_jobs:
                    break

        return self.filter_jobs(jobs_data)

    def filter_jobs(self, jobs_data) -> list[Job]:
        jobs = []
        for job_data in jobs_data:
            if job := self.filter_job(job_data):
                jobs.append(job)
        return jobs

    def filter_job(self, job) -> Job | None:
        link = job["guid"]
        posted_on = self.get_posted_on(job)
        if not self.validate_recency(link=link, posted_on=posted_on):
            return

        allowed_countries = {c.lower() for c in job["locationRestrictions"]}
        if allowed_countries and config.NATIVE_COUNTRY.lower() not in allowed_countries:
            job_rejected_logger.info(
                f"{link} is not available in {config.NATIVE_COUNTRY}. "
                f"Allowed countries: {', '.join(allowed_countries)}"
            )
            return

        title = job["title"]
        description = html.fromstring(job["description"]).text_content()
        # categories are of the format: [Django-Python-Developer, Python-Developer]
        categories = []
        for category in job["categories"]:
            categories.extend(category.split("-"))

        categories.extend(job["parentCategories"])

        if not self.validate_keywords_and_region(
            link=link,
            title=title,
            description=description,
            tags=categories,
        ):
            return

        max_salary = Decimal(str(job["maxSalary"]))
        if allowed_countries == {"india"}:
            # if the job is only available in India, then salary
            # is probably in INR. There is no direct field for currency
            # in the API response.
            max_salary = (max_salary * ExchangeRate.INR.value).quantize(Decimal("0.01"))

        if salary := self.validate_salary(link=link, salary=str(max_salary)):
            return Job(
                title=title,
                salary=salary,
                link=link,
                posted_on=posted_on,
            )

    def get_posted_on(self, job_data):
        return datetime.fromtimestamp(job_data["pubDate"]).astimezone(timezone.utc)
