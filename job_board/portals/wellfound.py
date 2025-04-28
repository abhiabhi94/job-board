import json
from datetime import datetime, timezone

from lxml import html

from job_board import config
from job_board.base import Job
from job_board.portals.base import BasePortal
from job_board.logger import job_rejected_logger, logger
from job_board.utils import (
    make_scrapfly_request,
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
            url = f"{self.url}?page={page_number}"
            content = make_scrapfly_request(url=url, asp=True)
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
