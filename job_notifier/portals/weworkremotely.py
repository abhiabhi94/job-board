import httpx
from lxml import objectify, html
import re

from job_notifier.logger import logger
from job_notifier.portals.base import BasePortal
from job_notifier.base import Message
from job_notifier.utils import parse_relative_time

# matches "60,000" or "60,000,000"
SALARY_REGEX = re.compile(r"\b\d{2,}(?:,\d{3})+\b")
# matches "posted 5 days ago" or "posted 5 hours ago"
POSTED_ON_REGEX = re.compile(
    r"\bposted\s(\d+\s+day[s]?\s+ago)\b|\bposted\s(\d+\s+hour[s]?\s+ago)\b"
)


class WeWorkRemotely(BasePortal):
    portal_name = "weworkremotely"
    region_mapping = {
        "remote": {
            "anywhere",
        },
    }

    url = "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss"

    def get_messages_to_notify(self) -> list[Message]:
        response = httpx.get(self.url)
        response.raise_for_status()
        root = objectify.fromstring(response.content)

        links_to_look = []
        for item in root.channel.item:
            link = item.link.text
            if self.validate_keywords_and_region(
                link=link,
                title=item.title.text,
                description=item.description.text,
                region=item.region.text,
            ):
                links_to_look.append(link)

        logger.debug(f"Found {links_to_look} links to look for salary information")
        messages_to_notify: list[Message] = []
        for link in links_to_look:
            if message := self.get_message_to_notify(link):
                messages_to_notify.append(message)
        return messages_to_notify

    def get_message_to_notify(self, link) -> Message | None:
        response = httpx.get(link)
        response.raise_for_status()
        root = html.fromstring(response.content)
        salary_elements = root.xpath(
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'salary')]"  # noqa: E501
        )
        salary = None
        for element in salary_elements:
            text_content = element.text_content().lower().strip()
            salary_matches = SALARY_REGEX.search(text_content)
            if salary_matches:
                salary = salary_matches.group()
                break

        validated_salary = self.validate_salary(link=link, salary=salary)
        if not validated_salary:
            return

        posted_on = None
        posted_on_elements = root.xpath(
            "//*[contains(text(), 'days ago') or contains(text(), 'day ago') or contains(text(), 'hours ago') or contains(text(), 'hour ago')]"  # noqa: E501
        )
        for element in posted_on_elements:
            text_content = element.text_content().lower().strip()
            posted_on_matches = POSTED_ON_REGEX.search(text_content)
            if posted_on_matches:
                posted_on_str = posted_on_matches.group(1)
                break

        posted_on = parse_relative_time(posted_on_str)

        return Message(
            title=root.findtext(".//title").strip(),
            salary=validated_salary,
            link=link,
            posted_on=posted_on,
        )
