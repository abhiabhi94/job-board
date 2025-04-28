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


SCRAPFLY_URL = "https://api.scrapfly.io/scrape"


class ScrapflyError(httpx.HTTPStatusError):
    """
    Custom exception to handle errors from the Scrapfly API.
    This is necessary because the Scrapfly API returns a 200 status code
    even when there is an error in the response.
    """

    def __init__(self, message, *, request, response, is_retryable=False):
        super().__init__(message=message, request=request, response=response)
        self.message = message
        self.request = request
        self.response = response
        self.is_retryable = is_retryable


def _raise_for_status(response) -> None:
    """
    Raises an HTTPStatusError if the response indicates an error.
    Helps to handle the response from the Scrapfly API similar to
    how httpx would handle it.
    This is necessary because the Scrapfly API returns a 200 status code
    even when there is an error in the response.

    https://scrapfly.io/docs/scrape-api/errors#web_scraping_api_error
    """
    result = response.json()["result"]
    logger.debug(f"Scrapfly monitoring link: {result['log_url']}")
    if result["success"]:
        return

    status_code = result["status_code"]
    url = result["url"]
    actual_request = httpx.Request("GET", url)
    actual_response = httpx.Response(
        status_code=status_code,
        request=actual_request,
        content=result["content"],
        headers=result["response_headers"],
    )
    error = result["error"]
    raise ScrapflyError(
        message=error["message"],
        request=actual_request,
        response=actual_response,
        is_retryable=error["retryable"],
    )


def make_scrapfly_request(
    url: str,
    *,
    asp=False,
    **kwargs,
) -> str:
    params = {
        "key": config.SCRAPFLY_API_KEY,
        "url": url,
        "asp": asp,
        "debug": True,
    }
    params.update(kwargs)
    if asp:
        # large timeout is required only when using asp.
        timeout = config.SCRAPFLY_REQUEST_TIMEOUT
    else:
        timeout = config.DEFAULT_HTTP_TIMEOUT

    with httpx_client() as client:
        # https://scrapfly.io/docs/scrape-api/getting-started#spec
        response = client.get(
            SCRAPFLY_URL,
            timeout=timeout,
            params=params,
        )
        _raise_for_status(response)

    return response.json()["result"]["content"]
