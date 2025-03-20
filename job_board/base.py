from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class Job(BaseModel):
    title: str
    salary: Decimal
    link: str
    posted_on: datetime | None
    location: str | None = None

    model_config = ConfigDict(frozen=True)
