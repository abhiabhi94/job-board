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
from job_board.portals.parser import JobParser
from job_board.utils import get_exchange_rate
from job_board.utils import httpx_async_client
from job_board.utils import retry_on_http_errors


class Parser(JobParser):
    def get_title(self) -> str:
        return self.item["title"]

    def get_description(self) -> str:
        return html.fromstring(self.item["description"]).text_content()

    def get_link(self) -> str:
        return self.item["guid"]

    def get_posted_on(self) -> datetime:
        return self._get_posted_on(self.item)

    @staticmethod
    def _get_posted_on(item) -> datetime:
        return datetime.fromtimestamp(item["pubDate"]).astimezone(timezone.utc)

    def get_is_remote(self) -> bool:
        # the API returns a list of countries
        # if the list is empty, then the job is remote
        return not self.item["locationRestrictions"]

    def get_locations(self):
        # the API returns a list of countries
        return self.item["locationRestrictions"]

    def get_tags(self) -> list[str]:
        # categories are of the format: [Django-Python-Developer, Python-Developer]
        tags = []
        for category in self.item["categories"] or []:
            tags.extend(category.split("-"))

        tags.extend(self.item["parentCategories"] or [])
        return tags

    def get_salary(self) -> Decimal | None:
        link = self.get_link()
        max_salary = self.item["maxSalary"]
        if not max_salary:
            return

        max_salary = Decimal(str(max_salary))
        currency = self.item["currency"]
        exchange_rate = get_exchange_rate(
            from_currency=currency,
            to_currency=config.DEFAULT_CURRENCY,
            exchange_date=self.get_posted_on(),
        )
        if not exchange_rate:
            logger.warning(
                f"[Himalayas]: No exchange rate found for {currency=}, {link=}"
            )
            exchange_rate = Decimal("1")

        max_salary = (max_salary / exchange_rate).quantize(Decimal("0.01"))

        return self.parse_salary(salary_str=str(max_salary))


MAX_JOBS_PER_REQUEST = 20  # Maximum jobs per request for the API


class Himalayas(BasePortal):
    """Docs: https://himalayas.app/api"""

    url = "https://himalayas.app/jobs/api"
    api_data_format = "json"
    portal_name = "himalayas"
    parser_class = Parser

    def make_request(self) -> list[dict[str, Any]]:
        if self.last_run_at:
            cutoff_date = self.last_run_at
        else:
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                config.JOB_AGE_LIMIT_DAYS
            )

        return asyncio.run(self.fetch_all_pages(cutoff_date=cutoff_date))

    async def fetch_all_pages(self, cutoff_date: datetime) -> List[Dict[str, Any]]:
        """
        Fetch all pages of job listings concurrently with proper error handling
        """
        async with httpx_async_client() as client:
            return await self._fetch_all_pages(client, cutoff_date)

    async def _fetch_all_pages(
        self, client: httpx.AsyncClient, cutoff_date: datetime
    ) -> List[Dict[str, Any]]:
        jobs_data = []
        jobs_fetched = 0
        # First request to get total count
        response = await self._make_async_request(
            client, params={"offset": 0, "limit": MAX_JOBS_PER_REQUEST}
        )
        total_jobs = response["totalCount"]
        job_data = response["jobs"]
        jobs_data.extend(job_data)
        jobs_fetched += len(job_data)

        logger.info(
            f"[Himalayas]: Fetched {jobs_fetched} of {total_jobs} jobs, "
            f"Remaining: {total_jobs - jobs_fetched}"
        )

        # Create batch tasks for remaining jobs
        while jobs_fetched < total_jobs:
            batch_tasks = []
            # Create batch of requests
            for batch_index in range(config.HIMALAYAS_REQUESTS_BATCH_SIZE):
                batch_offset = jobs_fetched + (batch_index * 20)
                if batch_offset >= total_jobs:
                    break

                batch_tasks.append(
                    self._make_async_request(
                        client,
                        params={"offset": batch_offset, "limit": 20},
                    )
                )

            if not batch_tasks:
                break

            # Execute all tasks in the batch concurrently
            # Since we're using tenacity for retries,
            # we don't need to handle exceptions here
            async with asyncio.TaskGroup() as tg:
                tasks = [tg.create_task(task) for task in batch_tasks]

            # Wait for all tasks to complete and collect results
            task_results = [t.result() for t in tasks]

            for result in task_results:
                batch_jobs = result["jobs"]
                # Check if all jobs in this batch are older than cutoff
                if all(cutoff_date > Parser._get_posted_on(j) for j in batch_jobs):
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

    @retry_on_http_errors(max_attempts=10, min_wait=1.5, max_wait=20)
    async def _make_async_request(
        self, client: httpx.AsyncClient, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        response = await client.get(self.url, params=params)
        response.raise_for_status()
        return response.json()

    def get_items(self, jobs_data) -> list:
        return jobs_data
