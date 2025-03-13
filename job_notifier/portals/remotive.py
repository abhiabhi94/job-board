import httpx
from lxml import html
from datetime import datetime

from job_notifier.portals.base import BasePortal
from job_notifier.base import Message


class Remotive(BasePortal):
    """https://github.com/remotive-com/remote-jobs-api"""

    portal_name = "remotive"
    region_mapping = {
        "remote": {
            "worldwide",
        },
    }

    url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=500"

    def get_messages_to_notify(self) -> list[Message]:
        response = httpx.get(self.url)
        response.raise_for_status()

        messages_to_notify: list[Message] = []
        jobs = response.json()["jobs"]
        for job in jobs:
            if message := self.get_message_to_notify(job):
                messages_to_notify.append(message)
        return messages_to_notify

    def get_message_to_notify(self, job):
        link = job["url"]
        title = job["title"]
        description = html.fromstring(job["description"]).text_content()
        region = job["candidate_required_location"]
        tags = job["tags"]

        if self.validate_keywords_and_region(
            link=link,
            title=title,
            description=description,
            region=region,
            tags=tags,
        ):
            if salary_range := job.get("salary"):
                # we just pick the max salary here.
                max_salary = salary_range.split("-")[-1].strip()
                # assumption is that salary is in USD
                # in future, introduce a currency field.
                if validated_salary := self.validate_salary(
                    link=link, salary=max_salary
                ):
                    posted_on = datetime.strptime(
                        job["publication_time"], "%Y-%m-%dT%H:%M:%S"
                    )
                    return Message(
                        link=link,
                        title=title,
                        salary=validated_salary,
                        posted_on=posted_on,
                    )
