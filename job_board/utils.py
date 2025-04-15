from datetime import datetime, timedelta, timezone
from enum import Enum
from decimal import Decimal
from functools import partial
import pathlib

import httpx
from jinja2 import Environment, FileSystemLoader

from job_board import config
from job_board.logger import logger


def response_hook(response: httpx.Response) -> None:
    response.raise_for_status()


def request_hook(request: httpx.Request) -> None:
    logger.debug(
        (f"Headers: {request.headers} Method: {request.method} URL: {request.url} ")
    )


httpx_client = partial(
    httpx.Client,
    timeout=httpx.Timeout(config.DEFAULT_HTTP_TIMEOUT),
    http2=True,
    event_hooks={"response": [response_hook], "request": [request_hook]},
)
jinja_env = Environment(
    loader=FileSystemLoader(pathlib.Path(__file__).parent / "templates"),
)


class ExchangeRate(Enum):
    """
    Constants for exchange rates, as of 31st March 2025.
    # use this link to find out the exchange rates
    https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@2025-03-31/v1/currencies/{currency_code}.json
    """

    USD = Decimal("1.0")
    INR = Decimal("0.012")
    EUR = Decimal("1.08")
    TRY = Decimal("0.03")
    JPY = Decimal("0.007")
    CAD = Decimal("0.75")


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
    CAD = "CAD"


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
