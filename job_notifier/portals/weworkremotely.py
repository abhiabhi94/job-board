import httpx
from lxml import objectify, html
import re
from decimal import Decimal

from job_notifier.logger import logger
from job_notifier.portals.base import BasePortal

# TODO: move these to a config file
KEYWORDS = {
    "python",
    "django",
    "flask",
    "fastapi",
    "sqlalchemy",
}
REGION = "remote"
SALARY = 60_000  # in USD


class WeWorkRemotely(BasePortal):
    region_mapping = {
        "remote": {
            "anywhere",
        },
    }

    url = "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss"

    ABOUT_SECTION_CLASS = "lis-container__job__sidebar__job-about__list"

    def get_links_to_notify(self):
        response = httpx.get(self.url)
        response.raise_for_status()
        root = objectify.fromstring(response.content)

        links_to_look = []
        for item in root.channel.item:
            title = item.title.text.lower()
            description = item.description.text.lower()
            region = item.region.text.lower()
            keyword_matches = KEYWORDS.intersection(
                title.split()
            ) or KEYWORDS.intersection(description.split())
            region_matches = self.region_mapping[REGION].intersection(region.split())

            if keyword_matches and region_matches:
                links_to_look.append(item.link.text)

        logger.debug(f"Found {len(links_to_look)} links to look for salary information")
        links_to_notify = []
        for link in links_to_look:
            response = httpx.get(link)
            response.raise_for_status()
            root = html.fromstring(response.content)
            (about_section,) = root.find_class(self.ABOUT_SECTION_CLASS)
            salary_element = None
            for element in about_section.iterchildren():
                if "salary" in element.text_content().lower().strip():
                    salary_element = element
                    break

            if salary_element is None:
                # no salary information, should we leave it to
                # the author???
                logger.debug(f"No salary information found for {link}")
                continue

            salary_info = salary_element.text_content().strip()
            salary_matches = re.search(r"^\D*(\d[\d,]*)", salary_info)
            salary = Decimal(str(salary_matches.group(1).replace(",", "")))
            if salary >= SALARY:
                links_to_notify.append(link)

        return links_to_notify
