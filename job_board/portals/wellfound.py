import json
from datetime import datetime, timezone

from lxml import html
import httpx

from job_board import config
from job_board.base import Job
from job_board.portals.base import BasePortal
from job_board.logger import job_rejected_logger, logger
from job_board.utils import (
    httpx_client,
)

SCRAPFLY_URL = "https://api.scrapfly.io/scrape"


class ScrapflyError(httpx.HTTPStatusError):
    """
    Custom exception to handle errors from the Scrapfly API.
    This is necessary because the Scrapfly API returns a 200 status code
    even when there is an error in the response.
    """

    def __init__(self, message, *, request, response, is_retryable=False):
        super().__init__(message=message, request=request, response=response)
        self.message = message
        self.request = request
        self.response = response
        self.is_retryable = is_retryable


def _raise_for_status(response):
    """
    Raises an HTTPStatusError if the response indicates an error.
    Helps to handle the response from the Scrapfly API similar to
    how httpx would handle it.
    This is necessary because the Scrapfly API returns a 200 status code
    even when there is an error in the response.

    https://scrapfly.io/docs/scrape-api/errors#web_scraping_api_error
    """
    result = response.json()["result"]
    logger.debug(f"Scrapfly monitoring link: {result['log_url']}")
    if result["success"]:
        return

    status_code = result["status_code"]
    url = result["url"]
    request = httpx.Request("GET", url)
    response = httpx.Response(
        status_code=status_code,
        request=request,
        content=result["content"],
        headers=result["response_headers"],
    )
    error = result["error"]
    raise ScrapflyError(
        message=error["message"],
        request=request,
        response=response,
        is_retryable=error["retryable"],
    )


class Wellfound(BasePortal):
    portal_name = "wellfound"
    # This url actually depends upon the keywords
    # Wellfound doesn't seem to provide tags that we can
    # use to filter the jobs
    # The generic URL is: https://wellfound.com/role/r/software-engineer
    # but that would require us to scrape a lot more pages and
    # each of them would have to bypass the detection.
    # For now, we are just hardcoding the url for python
    # developers.
    url = "https://wellfound.com/role/r/python-developer"
    api_data_format = "html"

    def get_jobs(self) -> list[Job]:
        page_number = 1
        jobs_data = []
        while True:
            with httpx_client() as client:
                # https://scrapfly.io/docs/scrape-api/getting-started#spec
                response = client.get(
                    SCRAPFLY_URL,
                    timeout=httpx.Timeout(config.SCRAPFLY_REQUEST_TIMEOUT),
                    params={
                        "key": config.SCRAPFLY_API_KEY,
                        "url": f"{self.url}?page={page_number}",
                        "debug": True,
                        "asp": True,
                    },
                )
                _raise_for_status(response)

            content = response.json()["result"]["content"]
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

        return self.filter_jobs(jobs_data)

    def filter_jobs(self, data) -> list[Job]:
        # data is a list of data from all pages.
        # we need to extract the job data from each page.
        jobs = []
        for job_data in data:
            job_results = [
                value
                for key, value in job_data.items()
                if key.startswith("JobListingSearchResult:")
            ]
            for job_result in job_results:
                if job := self.filter_job(job_result):
                    jobs.append(job)
        return jobs

    def filter_job(self, job_data) -> Job | None:
        slug = job_data["slug"]
        job_id = job_data["id"]
        link = f"https://wellfound.com/jobs/{job_id}-{slug}"

        if not job_data["remote"]:
            job_rejected_logger.info(f"Job {link} is not remote.")
            return

        allowed_locations = {c.lower() for c in job_data["locationNames"]}
        preferred_locations = {c.lower() for c in config.PREFERRED_CITIES}
        preferred_locations.update(
            [
                config.NATIVE_COUNTRY.lower(),
                # some jobs are remote but only available in certain
                # countries.
                # TODO: maybe do this based on a config, but we are already
                # checking for remote jobs.
                "remote",
            ]
        )
        if preferred_locations.isdisjoint(allowed_locations):
            job_rejected_logger.info(
                f"Job {link} is not available in {', '.join(preferred_locations)}. "
                f"Allowed locations: {', '.join(allowed_locations)}"
            )
            return

        posted_on = self.get_posted_on(job_data)
        if not self.validate_recency(link=link, posted_on=posted_on):
            return

        title = job_data["title"]
        description = job_data["description"]

        if not self.validate_keywords_and_region(
            link=link,
            title=title,
            description=description,
        ):
            return

        if salary := self.validate_salary_range(
            link=link, compensation=job_data["compensation"], range_separator="–"
        ):
            return Job(
                title=title,
                salary=salary,
                link=link,
                posted_on=posted_on,
            )

    def get_posted_on(self, job_data):
        return datetime.fromtimestamp(job_data["liveStartAt"]).astimezone(timezone.utc)
