import asyncio
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal
from typing import Any
from typing import Dict
from typing import List

import httpx
from lxml import html

from job_board import config
from job_board.logger import logger
from job_board.portals.base import BasePortal
from job_board.utils import get_exchange_rate
from job_board.utils import httpx_async_client
from job_board.utils import retry_on_http_errors


class Himalayas(BasePortal):
    """Docs: https://himalayas.app/api"""

    url = "https://himalayas.app/jobs/api"
    api_data_format = "json"
    portal_name = "himalayas"
    _REQUEST_BATCH_SIZE = 10  # Number of requests to process concurrently

    # def make_request(self) -> list[dict[str, Any]]:
    #     if self.last_run_at:
    #         cutoff_date = self.last_run_at
    #     else:
    #         cutoff_date = datetime.now(timezone.utc) - timedelta(
    #             config.JOB_AGE_LIMIT_DAYS
    #         )

    #     jobs_data = []
    #     jobs_fetched = 0
    #     while True:
    #         response = self._make_request(
    #           params={"offset": jobs_fetched, "limit": 20}
    #         )
    #         total_jobs = response["totalCount"]
    #         job_data = response["jobs"]
    #         jobs_data.extend(job_data)
    #         jobs_fetched += len(job_data)
    #         logger.info(
    #             (
    #                 f"[Himalayas]: Fetched {jobs_fetched} of {total_jobs} jobs, "
    #                 f"Remaining: {total_jobs - jobs_fetched}"
    #             )
    #         )

    #         # no need to make any more requests if we have
    #         # already fetched all the jobs that were posted
    #         # after the last run or all jobs are too old.
    #         if all(cutoff_date > self.get_posted_on(j) for j in job_data):
    #             logger.info(
    #                 f"[Himalayas]: No more jobs to fetch. "
    #                 f"{cutoff_date=}, {jobs_fetched=}"
    #             )
    #             break

    #         if jobs_fetched >= total_jobs:
    #             break

    #     return jobs_data

    # @retry_on_http_errors()
    # def _make_request(self, params):
    #     with httpx_client() as client:
    #         return client.get(
    #             self.url,
    #             params=params,
    #         ).json()

    @retry_on_http_errors(max_attempts=10, min_wait=1.5, max_wait=20)
    async def _make_async_request(
        self, client: httpx.AsyncClient, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Async version of your _make_request method with tenacity retry
        """
        response = await client.get(self.url, params=params)
        response.raise_for_status()
        return response.json()

    async def _fetch_all_pages(self, cutoff_date: datetime) -> List[Dict[str, Any]]:
        """
        Fetch all pages of job listings concurrently with proper error handling
        """
        jobs_data = []
        jobs_fetched = 0

        async with httpx_async_client() as client:
            # First request to get total count
            response = await self._make_async_request(
                client, params={"offset": 0, "limit": 20}
            )
            total_jobs = response["totalCount"]
            job_data = response["jobs"]
            jobs_data.extend(job_data)
            jobs_fetched += len(job_data)

            logger.info(
                f"[Himalayas]: Fetched {jobs_fetched} of {total_jobs} jobs, "
                f"Remaining: {total_jobs - jobs_fetched}"
            )

            if jobs_fetched >= total_jobs:
                return jobs_data

            # Create batch tasks for remaining jobs
            while jobs_fetched < total_jobs:
                batch_tasks = []
                # Create batch of requests
                for i in range(self._REQUEST_BATCH_SIZE):
                    if jobs_fetched + (i * 20) >= total_jobs:
                        break

                    batch_tasks.append(
                        self._make_async_request(
                            client,
                            params={"offset": jobs_fetched + (i * 20), "limit": 20},
                        )
                    )

                if not batch_tasks:
                    break

                # Execute all tasks in the batch concurrently
                # Since we're using tenacity for retries,
                # we don't need to handle exceptions here
                batch_results = await asyncio.gather(*batch_tasks)

                # Process results
                for result in batch_results:
                    batch_jobs = result["jobs"]
                    # Check if all jobs in this batch are older than cutoff
                    if all(cutoff_date > self.get_posted_on(j) for j in batch_jobs):
                        logger.info(
                            f"[Himalayas]: No more jobs to fetch. "
                            f"{cutoff_date=}, {jobs_fetched=}"
                        )
                        return jobs_data

                    jobs_data.extend(batch_jobs)
                    jobs_fetched += len(batch_jobs)

                    logger.info(
                        f"[Himalayas]: Fetched {jobs_fetched} of {total_jobs} jobs, "
                        f"Remaining: {total_jobs - jobs_fetched}"
                    )

                    if jobs_fetched >= total_jobs:
                        break

        return jobs_data

    def make_request(self) -> list[dict[str, Any]]:
        """
        Main method to fetch job listings with async implementation
        """
        if self.last_run_at:
            cutoff_date = self.last_run_at
        else:
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                config.JOB_AGE_LIMIT_DAYS
            )

        # Execute the async function
        jobs_data = asyncio.run(self._fetch_all_pages(cutoff_date=cutoff_date))

        # Here you would process the raw job data into Job objects
        # This part would depend on your original implementation

        return jobs_data

    def get_items(self, jobs_data) -> list:
        return jobs_data

    def get_title(self, item) -> str:
        return item["title"]

    def get_description(self, item) -> str:
        return html.fromstring(item["description"]).text_content()

    def get_link(self, item) -> str:
        return item["guid"]

    def get_posted_on(self, item) -> datetime:
        return datetime.fromtimestamp(item["pubDate"]).astimezone(timezone.utc)

    def is_remote(self, item) -> bool:
        # the API returns a list of countries
        # if the list is empty, then the job is remote
        return not item["locationRestrictions"]

    def get_locations(self, item):
        # the API returns a list of countries
        return item["locationRestrictions"]

    def get_tags(self, item) -> list[str]:
        # categories are of the format: [Django-Python-Developer, Python-Developer]
        tags = []
        for category in item["categories"]:
            tags.extend(category.split("-"))

        tags.extend(item["parentCategories"])
        return tags

    def get_salary(self, item) -> Decimal | None:
        link = self.get_link(item)
        max_salary = item["maxSalary"]
        if not max_salary:
            return

        max_salary = Decimal(str(max_salary))
        currency = item["currency"]
        exchange_rate = get_exchange_rate(
            from_currency=currency,
            to_currency=config.DEFAULT_CURRENCY,
            exchange_date=self.get_posted_on(item),
        )
        if not exchange_rate:
            logger.warning(
                f"[Himalayas]: No exchange rate found for {currency=}, {link=}"
            )
            exchange_rate = Decimal("1")

        max_salary = (max_salary / exchange_rate).quantize(Decimal("0.01"))

        return self.parse_salary(
            item=item,
            salary_str=str(max_salary),
        )
