import json
import urllib.parse

from job_board import config
from job_board.portals.base import BasePortal
from job_board.portals.parser import Job
from job_board.portals.parser import JobParser
from job_board.utils import httpx_client
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

    def get_tags(self):
        return [s["name"] for s in self.item["skills"]]

    def get_locations(self):
        locations = self.item["locations"]
        if locations:
            if not isinstance(locations[0], str):
                # This API sometimes returns weird data
                # like {"locations": [[['Remote - UK or Europe']]]}
                return []
        return self.item["locations"]


ALGOLIA_URL = "https://45bwzj1sgc-3.algolianet.com/1/indexes/*/queries"


class WorkAtAStartup(BasePortal):
    url = "https://www.workatastartup.com/companies/fetch"
    api_data_format = "json"
    portal_name = "work_at_a_startup"
    parser_class = Parser

    def make_request(self) -> list[Job]:
        template = jinja_env.get_template("work-at-a-startup-request-params.json")
        request_data = json.loads(template.render(hits_per_page=100))
        with httpx_client() as client:
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

        with httpx_client(
            cookies={"_bf_session_key": config.WORK_AT_A_STARTUP_COOKIE},
            headers={"x-csrf-token": config.WORK_AT_A_STARTUP_CSRF_TOKEN},
        ) as client:
            response = client.post(self.url, json={"ids": company_ids})

        return response.json()

    def get_items(self, data) -> list:
        # data is a list of data from all pages.
        # we need to extract the job data from each page.
        items = []
        for company in data["companies"]:
            items.extend(company["jobs"])
        return items
