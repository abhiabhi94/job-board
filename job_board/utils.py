import pathlib
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal
from enum import Enum
from functools import partial
from typing import Callable

import httpx
from jinja2 import Environment
from jinja2 import FileSystemLoader
from tenacity import retry
from tenacity import retry_if_exception
from tenacity import RetryCallState
from tenacity import stop_after_attempt
from tenacity import wait_exponential

from job_board import config
from job_board.logger import logger


def utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


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


def retry_on_http_errors(
    max_attempts: int = 5,
    additional_status_codes: list[int] | None = None,
    min_wait: float = 1,
    wait_multiplier: float = 1,
    max_wait: float = 5,
) -> Callable:
    """
    A retry decorator for HTTP errors.

    Args:
        max_attempts: Maximum number of retry attempts
        additional_status_codes: Additional HTTP status codes to retry on
        min_wait: Minimum wait time in seconds
        wait_multiplier: Multiplier for wait time
        max_wait: Maximum wait time in seconds

    Returns:
        A tenacity retry decorator configured for HTTP errors
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        retry=retry_if_exception(lambda e: _is_retryable(e, additional_status_codes)),
        wait=wait_exponential(min=min_wait, multiplier=wait_multiplier, max=max_wait),
        before_sleep=_before_sleep_logging,
        reraise=True,
    )


def _before_sleep_logging(retry_state: RetryCallState) -> None:
    """
    Logs information before retrying an operation.

    Args:
        retry_state: Current state of retry
    """
    logger.warning(
        (
            f"Retrying due to {retry_state.outcome.exception()!r}, "
            f"attempt: {retry_state.attempt_number}"
        )
    )


def _is_retryable(
    exception: Exception, additional_status_codes: list[int] | None = None
) -> bool:
    """
    Determines if an exception should trigger a retry.

    Args:
        exception: The exception to check
        additional_status_codes: Optional list of additional HTTP status codes
          to retry on

    Returns:
        True if the exception is retryable, False otherwise
    """
    if isinstance(exception, httpx.RequestError):
        return True

    if isinstance(exception, httpx.HTTPStatusError):
        status = exception.response.status_code
        retryable_codes = {429}

        # Add server errors
        retryable_codes.update(list(range(500, 600)))

        # Add any additional status codes provided
        if additional_status_codes:
            retryable_codes.update(additional_status_codes)

        return status in retryable_codes
    return False
