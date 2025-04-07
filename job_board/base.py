from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict
import humanize


class Job(BaseModel):
    title: str
    salary: Decimal
    link: str
    posted_on: datetime | None = None

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
            elif isinstance(value, (Decimal, int, float)):
                value = f"{value:,.2f}"

            formatted_values.append(f"{key_repr.ljust(max_key_length)}: {value}")

        return "\n".join(formatted_values)
