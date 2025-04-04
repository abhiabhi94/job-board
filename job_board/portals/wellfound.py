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

    def get_jobs(self):
        data = self.make_request()
        return self.filter_jobs(data)

    def make_request(self):
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

            json_response = response.json()
            result.append(json_response)

            if (
                json_response["data"]["talent"]["jobSearchResults"]["hasNextPage"]
                is False
            ):
                break

            page_count += 1
            data["variables"]["filterConfigurationInput"]["page"] = page_count

        return result

    def filter_jobs(self, data) -> list[Job]:
        # data is a list of data from all pages.
        # we need to extract the job data from each page.
        jobs = []
        for page_data in data:
            if jobs_data := self._filter_jobs(page_data):
                jobs.extend(jobs_data)
        return jobs

    def _filter_jobs(self, page_data) -> list[Job]:
        # Refer tests/mocked_responses/wellfound-page-1.json
        # for the structure of the data.
        jobs = []
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
                for job_listing in job_listings:
                    if job := self.filter_job(job_listing):
                        jobs.append(job)
        return jobs

    def filter_job(self, job_listing) -> Job | None:
        slug = job_listing["slug"]
        job_id = job_listing["id"]
        link = f"https://wellfound.com/jobs/{job_id}-{slug}"
        if not job_listing["remote"]:
            job_rejected_logger.debug(f"Job {link} is not remote.")
            return

        posted_on = datetime.fromtimestamp(job_listing["liveStartAt"]).astimezone(
            timezone.utc
        )
        if not self.validate_recency(link=link, posted_on=posted_on):
            return

        title = job_listing["title"]
        description = job_listing["description"]

        if not self.validate_keywords_and_region(
            link=link,
            title=title,
            description=description,
        ):
            return

        if salary := self.validate_salary_range(
            link=link,
            compensation=job_listing["compensation"],
            range_separator="–",
        ):
            return Job(
                title=title,
                salary=salary,
                link=link,
                posted_on=posted_on,
            )
