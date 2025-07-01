from datetime import datetime

from job_board.portals.parser import Job
from job_board.portals.parser import JobParser

PORTALS = {}


class BasePortal:
    portal_name: str
    url: str
    api_data_format: str
    parser_class: type[JobParser] = JobParser

    @classmethod
    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        PORTALS[cls.portal_name] = cls

    def __init__(self, last_run_at: None | datetime = None):
        self.last_run_at = last_run_at

    def fetch_jobs(self) -> list[Job]:
        """Fetch filtered jobs from the portal."""
        response = self.make_request()
        items = self.get_items(response)
        jobs = []
        for item in items:
            parser = self.parser_class(
                item=item,
                api_data_format=self.api_data_format,
            )
            if job := parser.get_job():
                jobs.append(job)
        return jobs

    def make_request(self) -> bytes | dict:
        """Makes a request to the portal and returns the response."""
        raise NotImplementedError()

    def get_items(self, response: bytes | dict) -> list[object]:
        """Parses the response and returns the items."""
        raise NotImplementedError()
