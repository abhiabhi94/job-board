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
            title = item.title.text.lower()
            description = item.description.text.lower()
            region = item.region.text.lower()
            keyword_matches = config.keywords.intersection(
                title.split()
            ) or config.keywords.intersection(description.split())
            region_matches = self.region_mapping[config.region].intersection(
                region.split()
            )

            if keyword_matches and region_matches:
                links_to_look.append(item.link.text)

        logger.debug(f"Found {len(links_to_look)} links to look for salary information")
        messages_to_notify = []
        for link in links_to_look:
            response = httpx.get(link)
            response.raise_for_status()
            root = html.fromstring(response.content)
            salary_elements = root.xpath(
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'salary')]"
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
                continue

            if salary <= config.salary:
                logger.debug(f"Salary {salary} for {link} is less than {config.salary}")
                continue

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

            messages_to_notify.append(
                Message(
                    title=root.findtext(".//title").strip(),
                    salary=salary,
                    link=link,
                    posted_on=posted_on,
                )
            )

        return messages_to_notify
