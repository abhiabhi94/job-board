import json

import urllib.parse

from job_board.portals.base import BasePortal
from job_board.base import Job
from job_board.utils import httpx_client, jinja_env
from job_board import config


ALGOLIA_URL = "https://45bwzj1sgc-3.algolianet.com/1/indexes/*/queries"


class WorkAtAStartup(BasePortal):
    url = "https://www.workatastartup.com/companies/fetch"
    api_data_format = "json"
    portal_name = "work_at_a_startup"

    def get_jobs(self) -> list[Job]:
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

        return self.filter_jobs(response.json())

    def filter_jobs(self, data) -> list[Job]:
        jobs = []
        for company in data["companies"]:
            for job_data in company["jobs"]:
                if job := self.filter_job(job_data):
                    jobs.append(job)
        return jobs

    def filter_job(self, job) -> Job | None:
        if job["remote"] not in {"yes", "only"}:
            return

        link = f"https://www.workatastartup.com/jobs/{job['id']}"
        # no date available regarding the job, so validate_recency
        # can't be used.
        title = job["title"]
        description = job["description"]
        skills = [s["name"] for s in job["skills"]]

        if not self.validate_keywords_and_region(
            link=link,
            title=title,
            description=description,
            tags=skills,
        ):
            return

        compensation = job["pretty_salary_range"]
        if salary := self.validate_salary_range(
            link=link,
            compensation=compensation,
            range_separator="-",
        ):
            return Job(
                title=title,
                salary=salary,
                link=link,
                posted_on=None,
            )
