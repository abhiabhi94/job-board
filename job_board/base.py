from datetime import datetime
from decimal import Decimal

import humanize
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class Job(BaseModel):
    title: str
    description: str | None = None
    link: str
    salary: Decimal | None = None
    posted_on: datetime | None = None
    tags: list[str] | None = Field(default_factory=list)
    is_remote: bool = False
    locations: list[str] | None = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)

    def __str__(self):
        model_dump = self.model_dump()
        max_key_length = (
            max(len(key) for key in model_dump) + 2  # Padding for alignment
        )

        formatted_values = []
        for key, value in model_dump.items():
            if value is None:
                value = "N/A"

            # Convert snake_case to Title Case
            key_repr = key.replace("_", " ").title()
            if isinstance(value, datetime):
                value = (humanize.naturaltime(value)).capitalize()
            elif isinstance(value, bool):
                value = "Yes" if value else "No"
            elif isinstance(value, (Decimal, int, float)):
                value = f"{value:,.2f}"
            elif isinstance(value, list):
                value = ", ".join(value)

            formatted_values.append(f"{key_repr.ljust(max_key_length)}: {value}")

        return "\n".join(formatted_values)
