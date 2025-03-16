import itertools

import httpx

from job_board.portals.base import BasePortal
from job_board.base import JobListing

RELEVANT_KEYS = {
    "title",
    "url",
    "salary",
    "tags",
    "candidate_required_location",
}


class Remotive(BasePortal):
    """https://github.com/remotive-com/remote-jobs-api"""

    portal_name = "remotive"
    url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=500"
    api_data_format = "json"

    region_mapping = {
        "remote": {
            "worldwide",
        },
    }

    def get_jobs_to_notify(self) -> list[JobListing]:
        # TODO: use a router from utils that set the default timeout
        # and retry for the request.
        response = httpx.get(self.url, timeout=httpx.Timeout(30))
        response.raise_for_status()

        jobs = response.json()["jobs"]

        # since the description is too long, we will remove it
        trimmed_response = []
        for job in jobs:
            trimmed_dict = {}
            for key, value in job.items():
                if key in RELEVANT_KEYS:
                    trimmed_dict[key] = value
            trimmed_response.append(trimmed_dict)

        # sending too many jobs at once will lead to exceeding the openai api limit
        # so we will need to finetune the number of jobs to send and the ways we
        # can send them.
        job_listings = []
        for batch in itertools.batched(trimmed_response, 100):
            job_listings.extend(self.process_jobs_with_llm(batch))
        return job_listings
