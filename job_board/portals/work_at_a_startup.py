import json
import urllib.parse

from job_board import config
from job_board.portals.base import BasePortal
from job_board.portals.parser import Job
from job_board.portals.parser import JobParser
from job_board.utils import get_iso2
from job_board.utils import http_client
from job_board.utils import jinja_env


class Parser(JobParser):
    def get_link(self) -> str:
        return f"https://www.workatastartup.com/jobs/{self.item['id']}"

    def get_title(self):
        return self.item["title"]

    def get_description(self):
        return self.item["description"]

    def get_posted_on(self):
        return None

    def get_salary_range(self):
        compensation = self.item["pretty_salary_range"]
        return self.parse_salary_range(compensation=compensation)

    def get_is_remote(self) -> bool:
        return self.item["remote"].lower() in {"yes", "only"}

    def get_tags(self) -> list[str]:
        return [s["name"] for s in self.item["skills"]]

    def get_locations(self) -> list[str]:
        return self.parse_locations(self.item["locations"])

    @staticmethod
    def parse_locations(locations: list[str]) -> list[str]:
        # this API can return the same location in different formats
        # so, keeping this as a set to avoid duplicates.
        parsed_locations = set()
        for location in locations:
            if not isinstance(location, str):
                continue

            country = None
            if location.count(",") == 2:
                # example: "New York, NY, USA"
                _, _, country = location.split(",")
            elif location.count(",") == 1:
                _, country = location.split(",")

            if country is not None:
                # the format of locations for this API is too inconsistent
                # to be considering both subdivision and country.
                # they are some times returned as full names,
                # sometimes abbreviations, sometimes codes etc,
                location = country
            if iso_code := get_iso2(location):
                parsed_locations.add(iso_code)
        return list(parsed_locations)

    def get_company_name(self) -> str:
        return self.item["_company"]["name"]


ALGOLIA_URL = "https://45bwzj1sgc-3.algolianet.com/1/indexes/*/queries"


class WorkAtAStartup(BasePortal):
    portal_name = "workatastartup"
    base_url = "https://www.workatastartup.com"
    display_name = "Work At A Startup"
    url = "https://www.workatastartup.com/companies/fetch"
    api_data_format = "json"
    parser_class = Parser

    def make_request(self) -> list[Job]:
        template = jinja_env.get_template("work-at-a-startup-request-params.json")
        request_data = json.loads(template.render(hits_per_page=100))
        with http_client() as client:
            response = client.post(
                ALGOLIA_URL,
                params=request_data["query_params"],
                json={
                    "requests": [
                        {
                            "indexName": (
                                "WaaSPublicCompanyJob_created_at_desc_production"
                            ),
                            "params": urllib.parse.urlencode(request_data["params"]),
                        }
                    ]
                },
            )

        company_ids = [
            hit["company_id"]
            for result in response.json()["results"]
            for hit in result["hits"]
        ]

        cookies = {
            "_bf_session_key": config.WORK_AT_A_STARTUP_COOKIE,
        }
        headers = {
            "x-csrf-token": config.WORK_AT_A_STARTUP_CSRF_TOKEN,
        }
        with http_client(
            cookies=cookies,
            headers=headers,
        ) as client:
            response = client.post(
                self.url,
                json={"ids": company_ids},
            )

        return response.json()

    def get_items(self, data) -> list:
        # data is a list of data from all pages.
        # we need to extract the job data from each page.
        items = []
        for company in data["companies"]:
            # Create a copy of company data without 'jobs' to avoid circular reference
            # when serializing job items that contain the company reference
            company_copy = dict(company)
            company_copy.pop("jobs", None)
            for job in company["jobs"]:
                job["_company"] = company_copy
                items.append(job)
        return items
