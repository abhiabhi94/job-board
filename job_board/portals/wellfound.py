import asyncio
import json
from datetime import datetime
from datetime import timezone
from typing import Any

from lxml import html

from job_board import config
from job_board.logger import logger
from job_board.portals.base import BasePortal
from job_board.portals.parser import JobParser
from job_board.utils import make_scrapfly_async_request
from job_board.utils import retry_on_http_errors


class Parser(JobParser):
    def get_link(self):
        slug = self.item["slug"]
        job_id = self.item["id"]
        return f"https://wellfound.com/jobs/{job_id}-{slug}"

    def get_is_remote(self):
        return self.item["remote"]

    def get_locations(self):
        return self.item["locationNames"]

    def get_posted_on(self):
        return datetime.fromtimestamp(
            self.item["liveStartAt"],
        ).astimezone(timezone.utc)

    def get_title(self):
        return self.item["title"]

    def get_description(self):
        return self.item["description"]

    def get_salary_range(self):
        compensation = self.item["compensation"]
        return self.parse_salary_range(compensation=compensation)

    def get_tags(self):
        # Tags are not directly available in the job data.
        # for now, we will just return software developer as a tag
        # so that these jobs can be discovered.
        return ["developer"]


class Wellfound(BasePortal):
    portal_name = "wellfound"
    url = "https://wellfound.com/role/r/software-engineer"
    # although the API returns HTML, but the JSON content is embedded in the HTML
    # so we will treat it as JSON for our purposes.
    api_data_format = "json"
    parser_class = Parser

    def make_request(self) -> list[dict[str, Any]]:
        return asyncio.run(self._fetch_all_pages())

    async def _fetch_all_pages(self) -> list[dict[str, Any]]:
        # First, get the first page to determine total pages
        first_page_url = f"{self.url}?page=1"
        first_page_content = await self._make_request(first_page_url)
        graph_data = self._parse_page_content(first_page_content)
        total_pages = self._get_total_pages(graph_data)
        logger.info(f"[Wellfound]: Fetched page=1, found {total_pages=}")

        jobs_data = [graph_data]  # Start with first page data
        current_page = (
            2  # Start from the second page since the first is already fetched
        )
        while current_page <= total_pages:
            # Process remaining pages in batches
            batch_end = min(
                # for example: 2nd batch will be 2 + 11 - 1 = 12
                current_page + config.WELLFOUND_REQUESTS_BATCH_SIZE - 1,
                total_pages,
            )
            batch_pages = list(
                range(
                    current_page,
                    batch_end + 1,  # End is exclusive, so we add 1.
                )
            )
            batch_urls = [f"{self.url}?page={page}" for page in batch_pages]

            logger.info(
                (
                    "[Wellfound]: Fetching pages in batch, "
                    f"total pages: {total_pages}, "
                    f"batch info: pages {batch_pages[0]}-{batch_pages[-1]}"
                )
            )
            async with asyncio.TaskGroup() as tg:
                tasks = [tg.create_task(self._make_request(url)) for url in batch_urls]

            task_results = [t.result() for t in tasks]
            for page_num, result in zip(batch_pages, task_results, strict=True):
                graph_data = self._parse_page_content(result)
                total_pages = self._get_total_pages(graph_data)
                jobs_data.append(graph_data)
                logger.info(f"[Wellfound]: Processed page {page_num}")

            current_page = batch_end + 1  # Move to the next batch

        return jobs_data

    @retry_on_http_errors(
        additional_status_codes=[403, 422],
        max_attempts=10,
        # Reduce the retry attempts and wait time for faster response
        min_wait=5,
        max_wait=30,
    )
    async def _make_request(self, url: str) -> str:
        return await make_scrapfly_async_request(url, asp=True)

    def _parse_page_content(self, content: str) -> dict[str, Any]:
        element = html.fromstring(content)
        data_element = element.get_element_by_id("__NEXT_DATA__")
        data = json.loads(data_element.text)
        return data["props"]["pageProps"]["apolloState"]["data"]

    def _get_total_pages(self, graph_data: dict[str, Any]) -> int:
        talent_data = graph_data["ROOT_QUERY"]["talent"]
        for key, value in talent_data.items():
            if key.startswith("seoLandingPageJobSearchResults({"):
                return value["pageCount"]
        return 1

    def get_items(self, jobs_data) -> list:
        # data is a list of data from all pages.
        # we need to extract the job data from each page.
        items = []
        for job_data in jobs_data:
            job_results = [
                value
                for key, value in job_data.items()
                if key.startswith("JobListingSearchResult:")
            ]
            items.extend(job_results)
        return items
