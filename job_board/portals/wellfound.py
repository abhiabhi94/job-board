from decimal import Decimal
from datetime import datetime, timezone

import httpx

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
    url = "https://wellfound.com/graphql"
    api_data_format = "html"

    def get_jobs(self):
        data = self.make_request()
        return self.filter_jobs(data)

    def make_request(self):
        headers = {
            "accept-language": "en-GB,en;q=0.8",
            "referer": "https://wellfound.com/jobs",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 "
                "Safari/537.36"
            ),
            "x-apollo-operation-name": "JobSearchResultsX",
            "x-apollo-signature": f"{config.WELLFOUND_APOLLO_SIGNATURE}",
            "x-requested-with": "XMLHttpRequest",
        }
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
        cookies = {
            "datadome": f"{config.WELLFOUND_DATADOME_COOKIE}",
            "_wellfound": f"{config.WELLFOUND_COOKIE}",
        }

        result = []
        page_count = 1
        while True:
            logger.debug(f"[{self.portal_name}] Fetching page {page_count}...")

            response = httpx.post(
                self.url,
                headers=headers,
                json=data,
                cookies=cookies,
                timeout=httpx.Timeout(30),
            )

            response.raise_for_status()
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

        compensation = job_listing["compensation"]
        if not compensation:
            job_rejected_logger.debug(f"Job {link} has no compensation.")
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
                    f"Salary {salary_in_dollars} for {link} is less than "
                    f"{config.SALARY:,}"
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
            raise InvalidSalary(f"Job {link} has no salary info.")

        symbol = salary_info[0].lower()

        try:
            currency = Currency(symbol)
        except ValueError:
            raise ValueError(f"Job {link} has unsupported currency symbol {symbol}.")

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
