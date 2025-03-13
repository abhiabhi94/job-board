from decimal import Decimal, InvalidOperation

from job_notifier.base import Message
from job_notifier import config
from job_notifier.logger import logger


class BasePortal:
    portal_name: str
    url: str
    region_mapping: dict[str, set[str]]

    def get_messages_to_notify(self) -> list[Message]:
        raise NotImplementedError()

    def get_message_to_notify(self, job) -> Message:
        raise NotImplementedError()

    def validate_keywords_and_region(
        self, *, link, title, description, region, tags=None
    ) -> bool:
        logger.debug(f"Validating keywords and region for {link}")

        title = title.lower()
        description = description.lower()
        region = region.lower()
        if not tags:
            tags = []
        tags = [tag.lower() for tag in tags]
        keywords = config.KEYWORDS

        keyword_matches = (
            keywords.intersection(title.split())
            or keywords.intersection(description.split())
            or keywords.intersection(tags)
        )

        if not keyword_matches:
            logger.debug(f"No keyword matches found for {link}")
            return False

        region_matches = self.region_mapping[config.REGION].intersection(region.split())
        if not region_matches:
            logger.debug(f"No region matches found for {link}")
            return False

        return True

    def validate_salary(self, *, link: str, salary: str) -> str | None:
        logger.debug(f"Looking for salary information in {link}")

        if salary is None:
            # no salary information, should we still consider this relevant ???
            logger.debug(f"No salary information found for {link}")
            return

        salary = salary.replace("$", "").replace(",", "")
        try:
            salary = Decimal(str(salary))
        except InvalidOperation:
            logger.debug(f"Invalid salary {salary} for {link}")
            return

        if salary <= config.SALARY:
            logger.debug(f"Salary {salary} for {link} is less than {config.SALARY}")
            return

        return salary
