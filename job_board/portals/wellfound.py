import json
from decimal import Decimal
from datetime import datetime, timezone

from job_board import config
from job_board.base import Job
from job_board.portals.base import BasePortal
from job_board.logger import job_rejected_logger, logger
from job_board.utils import (
    httpx_client,
    jinja_env,
)


class Wellfound(BasePortal):
    portal_name = "wellfound"
    url = "https://wellfound.com/graphql"
    api_data_format = "html"

    def get_jobs(self) -> list[Job]:
        data = self.make_request()
        return self.filter_jobs(data)

    def make_request(self) -> list[dict]:
        template = jinja_env.get_template("wellfound-request-params.json")
        params = json.loads(
            template.render(
                wellfound_apollo_signature=config.WELLFOUND_APOLLO_SIGNATURE,
                wellfound_datadome_cookie=config.WELLFOUND_DATADOME_COOKIE,
                wellfound_cookie=config.WELLFOUND_COOKIE,
            )
        )
        data = {
            "operationName": "JobSearchResultsX",
            "variables": {
                "filterConfigurationInput": {
                    "page": 1,
                    # countries where the job is available,
                    # this is for india and asia.
                    "remoteCompanyLocationTagIds": ["1647", "153509"],
                    # this is for software developer.
                    "roleTagIds": ["151647"],
                    "equity": {"min": None, "max": None},
                    "remotePreference": "REMOTE_OPEN",
                    # for some reason this accepts salary in thousands
                    "salary": {
                        "min": int(config.SALARY // Decimal(str(1_000))),
                        "max": None,
                    },
                    "yearsExperience": {"min": 4, "max": None},
                    "sortBy": "LAST_POSTED",
                }
            },
            "extensions": {
                "operationId": (
                    "tfe/2aeb9d7cc572a94adfe2b888b32e64eb8b7fb77215b168ba4256b08f9a94f37b"
                ),
            },
        }

        result = []
        page_count = 1
        while True:
            logger.debug(f"[{self.portal_name}] Fetching page {page_count}...")

            with httpx_client(
                cookies=params["cookies"], headers=params["headers"]
            ) as client:
                response = client.post(self.url, json=data)

            page_data = response.json()
            job_data = self.get_job_data(page_data)
            result.append(job_data)

            if last_run_at := self.last_run_at:
                # we don't want to go through all
                # the jobs if we have already seen them.

                # wellfound has promoted job listings which are sent first
                # and then the normal job listings. these promoted listings
                # are sent in every page, despite the API request for jobs
                # being sorted by posted date.
                # so we are checking the most recent job listing among all the
                # listings in the page, to be sure that we are not missing any jobs.
                most_recent_listing = max(
                    job_data, key=lambda job: self.get_posted_on(job)
                )
                most_recent = self.get_posted_on(most_recent_listing)

                if most_recent < last_run_at:
                    break

            if page_data["data"]["talent"]["jobSearchResults"]["hasNextPage"] is False:
                break

            page_count += 1
            data["variables"]["filterConfigurationInput"]["page"] = page_count

        return result

    def get_job_data(self, page_data) -> list[dict]:
        job_data = []
        for company_edge in page_data["data"]["talent"]["jobSearchResults"]["startups"][
            "edges"
        ]:
            company_node = company_edge["node"]
            company_type = company_node["__typename"]
            match company_type:
                case "FeaturedStartups":
                    companies = company_node["featuredStartups"]
                case "PromotedResult" | "StartupSearchResult":
                    companies = [company_node]
                case _:
                    raise ValueError(f"Unknown company node type: {company_type}")

            for company in companies:
                result_type = company["__typename"]
                match result_type:
                    case "PromotedResult":
                        company_data = company["promotedStartup"]
                    case "StartupSearchResult":
                        company_data = company
                    case _:
                        raise ValueError(f"Unknown company data type: {result_type}")

                job_listings = company_data["highlightedJobListings"]
                job_data.extend(job_listings)

        return job_data

    def filter_jobs(self, data) -> list[Job]:
        # data is a list of data from all pages.
        # we need to extract the job data from each page.
        jobs = []
        for page_data in data:
            for job_data in page_data:
                if job := self.filter_job(job_data):
                    jobs.append(job)
        return jobs

    def filter_job(self, job_data) -> Job | None:
        slug = job_data["slug"]
        job_id = job_data["id"]
        link = f"https://wellfound.com/jobs/{job_id}-{slug}"
        if not job_data["remote"]:
            job_rejected_logger.info(f"Job {link} is not remote.")
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
            link=link,
            compensation=job_data["compensation"],
            range_separator="–",
        ):
            return Job(
                title=title,
                salary=salary,
                link=link,
                posted_on=posted_on,
            )

    def get_posted_on(self, job_data):
        return datetime.fromtimestamp(job_data["liveStartAt"]).astimezone(timezone.utc)
