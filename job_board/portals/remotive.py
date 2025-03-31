import itertools
from datetime import datetime, timezone

import httpx

from job_board.portals.base import BasePortal
from job_board.base import Job

RELEVANT_KEYS = {
    "title",
    "url",
    "salary",
    "tags",
    "candidate_required_location",
    "publication_date",
}

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


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

    def get_jobs(self) -> list[Job]:
        # TODO: use a router from utils that set the default timeout
        # and retry for the request.
        response = httpx.get(self.url, timeout=httpx.Timeout(30))
        response.raise_for_status()

        jobs_data = response.json()
        return self.filter_jobs(jobs_data)

    def filter_jobs(self, data) -> list[Job]:
        jobs_data = data["jobs"]
        # remove irrelevant data, so that we
        # don't send too much data to the openai api
        recent_jobs_data = []
        for job_data in jobs_data:
            link = job_data["url"]
            published_on = (
                datetime.strptime(job_data["publication_date"], DATE_FORMAT)
            ).astimezone(timezone.utc)

            if not self.validate_recency(link=link, posted_on=published_on):
                continue

            recent_job_data = {}
            for key, value in job_data.items():
                if key in RELEVANT_KEYS:
                    recent_job_data[key] = value

            recent_jobs_data.append(recent_job_data)

        # sending too many jobs at once will lead to exceeding the openai api limit
        # so we will need to finetune the number of jobs to send and the ways we
        # can send them.
        jobs = []
        for batch in itertools.batched(recent_jobs_data, 100):
            jobs.extend(self.filter_jobs_with_llm(batch))
        return jobs
