import httpx
from lxml import objectify, html
import re
from decimal import Decimal

from job_notifier.logger import logger
from job_notifier.portals.base import BasePortal
from job_notifier import config
from job_notifier.base import Message

# matches "60,000" or "60,000,000"
SALARY_REGEX = re.compile(r"\b\d{2,}(?:,\d{3})+\b")
# matches "posted 5 days ago" or "posted 5 hours ago"
POSTED_ON_REGEX = re.compile(
    r"\bposted\s(\d+\s+days\s+ago)\b|\bposted\s(\d+\s+hours\s+ago)\b"
)


class WeWorkRemotely(BasePortal):
    region_mapping = {
        "remote": {
            "anywhere",
        },
    }

    url = "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss"

    def get_messages_to_notify(self):
        response = httpx.get(self.url)
        response.raise_for_status()
        root = objectify.fromstring(response.content)

        links_to_look = []
        for item in root.channel.item:
            if self.match_keywords_and_region(
                title=item.title.text,
                description=item.description.text,
                region=item.region.text,
            ):
                links_to_look.append(item.link.text)

        logger.debug(f"Found {links_to_look} links to look for salary information")
        messages_to_notify: list[Message] = []
        for link in links_to_look:
            if message := self.get_message_to_notify(link):
                messages_to_notify.append(message)
        return messages_to_notify

    def match_keywords_and_region(self, *, title, description, region) -> bool:
        title = title.lower()
        description = description.lower()
        region = region.lower()

        keyword_matches = config.keywords.intersection(
            title.split()
        ) or config.keywords.intersection(description.split())
        region_matches = self.region_mapping[config.region].intersection(region.split())

        return bool(keyword_matches and region_matches)

    def get_message_to_notify(self, link) -> Message | None:
        logger.debug(f"Looking for salary information in {link}")

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
                salary = Decimal(str(salary_matches.group().replace(",", "")))
                break

        if salary is None:
            # no salary information, should we still consider this relevant ???
            logger.debug(f"No salary information found for {link}")
            return

        if salary <= config.salary:
            logger.debug(f"Salary {salary} for {link} is less than {config.salary}")
            return

        posted_on = None
        posted_on_elements = root.xpath(
            "//*[contains(text(), 'days ago') or contains(text(), 'hours ago')]"
        )
        for element in posted_on_elements:
            text_content = element.text_content().lower().strip()
            posted_on_matches = POSTED_ON_REGEX.search(text_content)
            if posted_on_matches:
                posted_on = posted_on_matches.group(1)
                break

        return Message(
            title=root.findtext(".//title").strip(),
            salary=salary,
            link=link,
            posted_on=posted_on,
        )
