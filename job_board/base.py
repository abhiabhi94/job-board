from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(kw_only=True, frozen=True)
class JobListing:
    title: str
    salary: Decimal
    link: str
    posted_on: datetime | None
