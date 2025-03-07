from typing import NamedTuple
from datetime import datetime
from decimal import Decimal


class Message(NamedTuple):
    title: str
    salary: Decimal
    link: str
    # some websites don't provide the date of posting
    # but directly provide the time passed since posting
    # for example: posted 5 days ago.
    posted_on: datetime | str | None = None
