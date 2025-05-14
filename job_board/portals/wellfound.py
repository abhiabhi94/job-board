import json
from datetime import datetime
from datetime import timezone

from lxml import html

from job_board.base import Job
from job_board.logger import logger
from job_board.portals.base import BasePortal
from job_board.utils import make_scrapfly_request
from job_board.utils import retry_on_http_errors


class Wellfound(BasePortal):
    portal_name = "wellfound"
    url = "https://wellfound.com/role/r/software-engineer"
    api_data_format = "html"

    def make_request(self) -> list[Job]:
        page_number = 1
        jobs_data = []
        while True:
            url = f"{self.url}?page={page_number}"
            content = self._make_request(url)
            element = html.fromstring(content)
            # graphQL data is embeded in this element
            data_element = element.get_element_by_id("__NEXT_DATA__")
            data = json.loads(data_element.text)
            # this is the data we need
            graph_data = data["props"]["pageProps"]["apolloState"]["data"]
            jobs_data.append(graph_data)
            talent_data = graph_data["ROOT_QUERY"]["talent"]
            for key, value in talent_data.items():
                if key.startswith("seoLandingPageJobSearchResults({"):
                    break

            total_pages = value["pageCount"]
            logger.info(f"[Wellfound]: On {page_number=}, {total_pages=}")
            page_number += 1
            if page_number > total_pages:
                break

        return jobs_data

    @retry_on_http_errors(additional_status_codes=[403])
    def _make_request(self, url: str) -> str:
        return make_scrapfly_request(url, asp=True)

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

    def get_link(self, item):
        slug = item["slug"]
        job_id = item["id"]
        return f"https://wellfound.com/jobs/{job_id}-{slug}"

    def is_remote(self, item):
        return item["remote"]

    def get_locations(self, item):
        return item["locationNames"]

    def get_posted_on(self, item):
        return datetime.fromtimestamp(item["liveStartAt"]).astimezone(timezone.utc)

    def get_title(self, item):
        return item["title"]

    def get_description(self, item):
        return item["description"]

    def get_salary(self, item):
        link = self.get_link(item)
        compensation = item["compensation"]
        return self.parse_salary_range(
            link=link,
            compensation=compensation,
            range_separator="–",
        )
