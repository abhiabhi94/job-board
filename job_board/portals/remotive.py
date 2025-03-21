import itertools
from datetime import datetime, timedelta, timezone

import httpx

from job_board.portals.base import BasePortal
from job_board.base import Job
from job_board.logger import logger
from job_board import config

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

        jobs_data = response.json()["jobs"]

        # remove irrelevant data, so that we
        # don't send too much data to the openai api
        now = datetime.now(timezone.utc)
        recent_jobs_data = []
        for job_data in jobs_data:
            published_on = (
                datetime.strptime(job_data["publication_date"], DATE_FORMAT)
            ).astimezone(timezone.utc)
            if (now - published_on) > timedelta(days=config.JOB_AGE_LIMIT_DAYS):
                logger.debug(f"Removing older job: {job_data['url']}")
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
            jobs.extend(self.process_jobs_with_llm(batch))
        return jobs
