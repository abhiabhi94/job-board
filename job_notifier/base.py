from typing import NamedTuple
from datetime import datetime
from decimal import Decimal


class Message(NamedTuple):
    title: str
    salary: Decimal
    link: str
    posted_on: datetime | None
