from datetime import datetime

import sqlalchemy as sa

from job_board.connection import get_session
from job_board.logger import logger
from job_board.models import Job
from job_board.portals.parser import Job as JobListing
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

    def fetch_jobs(self) -> list[JobListing]:
        """Fetch jobs from the portal."""
        response = self.make_request()
        items = self.get_items(response)
        jobs = []
        relevant_items = self.filter_items(items)
        for item in relevant_items:
            parser = self.parser_class(
                item=item,
                api_data_format=self.api_data_format,
            )
            job = parser.get_job()
            jobs.append(job)
        return jobs

    def filter_items(self, items: list[object]) -> list[object]:
        recent_links = []
        parsers = []
        for item in items:
            parser = self.parser_class(
                item=item,
                api_data_format=self.api_data_format,
            )
            link = parser.get_link()
            if not parser.validate_recency():
                posted_on = parser.get_posted_on()
                logger.info(f"{link=} {posted_on=} is too old, skipping.")
                continue

            recent_links.append(link)
            parsers.append(parser)

        statement = sa.select(Job.link).where(
            sa.func.lower(Job.link).in_([link.lower() for link in recent_links])
        )
        with get_session(readonly=True) as session:
            existing_links = session.execute(statement).scalars().all()

        relevant_items = []
        for parser in parsers:
            link = parser.get_link()
            if link in existing_links:
                logger.info(f"Job {link} already exists, skipping.")
                continue
            relevant_items.append(parser.item)
        return relevant_items

    def make_request(self) -> bytes | dict:
        """Makes a request to the portal and returns the response."""
        raise NotImplementedError()

    def get_items(self, response: bytes | dict) -> list[object]:
        """Parses the response and returns the items."""
        raise NotImplementedError()
