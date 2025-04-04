from datetime import datetime, timedelta, timezone
from enum import Enum
from decimal import Decimal
from functools import partial
import pathlib

import httpx
from jinja2 import Environment, FileSystemLoader

from job_board import config


def response_hook(response: httpx.Response) -> None:
    response.raise_for_status()


httpx_client = partial(
    httpx.Client,
    timeout=httpx.Timeout(config.DEFAULT_HTTP_TIMEOUT),
    http2=True,
    event_hooks={"response": [response_hook]},
)
jinja_env = Environment(
    loader=FileSystemLoader(pathlib.Path(__file__).parent / "templates"),
)


class ExchangeRate(Enum):
    """
    Constants for exchange rates, as of 31st March 2025.
    """

    USD = Decimal("1.0")
    INR = Decimal("0.012")
    EUR = Decimal("1.08")
    TRY = Decimal("0.03")
    JPY = Decimal("0.007")


class Currency(Enum):
    """
    Constants for currency symbols.
    """

    USD = "$"
    INR = "₹"
    EUR = "€"
    # turkish lira
    TRY = "₺"
    JPY = "¥"


def parse_relative_time(relative_str: str | None) -> datetime | None:
    if relative_str is None:
        return

    value, unit = relative_str.replace(" ago", "").split(" ")
    value = int(value)

    now = datetime.now(timezone.utc)

    match unit:
        case "day" | "days":
            return now - timedelta(days=value)
        case "hour" | "hours":
            return now - timedelta(hours=value)
        case "minute" | "minutes":
            return now - timedelta(minutes=value)
        case "second" | "seconds":
            return now - timedelta(seconds=value)
        case "month" | "months":
            # although this might be a little inaccurate
            # don't want to use another library dateutil
            # for just this one case.
            return now - timedelta(days=30 * value)
        case _:
            raise ValueError(f"Unsupported time unit: {unit}")
