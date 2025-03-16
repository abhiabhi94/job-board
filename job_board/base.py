from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class JobListing(BaseModel):
    title: str
    salary: Decimal
    link: str
    posted_on: datetime

    model_config = ConfigDict(frozen=True)
