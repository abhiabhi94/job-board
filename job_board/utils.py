import pathlib
from datetime import datetime
from datetime import timezone
from decimal import Decimal
from functools import partial
from typing import Any
from typing import Callable

import httpx
import pycountry
from babel.numbers import get_currency_symbol
from jinja2 import Environment
from jinja2 import FileSystemLoader
from tenacity import retry
from tenacity import retry_if_exception
from tenacity import RetryCallState
from tenacity import stop_after_attempt
from tenacity import wait_exponential

from job_board import config
from job_board.logger import logger


EXCHANGE_RATE_API_URL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date}/v1/currencies/{currency}.json"
EXCHANGE_RATE_FALLBACK_API_URL = (
    "https://{date}.currency-api.pages.dev/v1/currencies/{currency}.json"
)


def utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def response_hook(response: httpx.Response) -> None:
    response.raise_for_status()


async def response_hook_async(response: httpx.Response) -> None:
    """
    Asynchronous response hook to raise for status.
    This is used with httpx.AsyncClient.
    """
    response.raise_for_status()


httpx_client = partial(
    httpx.Client,
    timeout=httpx.Timeout(config.DEFAULT_HTTP_TIMEOUT),
    http2=True,
    event_hooks={"response": [response_hook]},
)
httpx_async_client = partial(
    httpx.AsyncClient,
    timeout=httpx.Timeout(config.DEFAULT_HTTP_TIMEOUT),
    http2=True,
    event_hooks={"response": [response_hook_async]},
)
jinja_env = Environment(
    loader=FileSystemLoader(pathlib.Path(__file__).parent / "templates"),
)


def get_currency_from_symbol(symbol: str, locale: str = "en_US") -> str | None:
    symbol_map = _build_symbol_to_code_map(locale)
    return symbol_map.get(symbol)


_SYMBOL_CACHE: dict[str, str] | None = None


def _build_symbol_to_code_map(locale: str = config.DEFAULT_LOCALE) -> dict[str, str]:
    """
    both pycountry and babel don't provide a way to get
    currency from symbol, so we build a mapping that is
    generated from babel's currency symbols.
    This is a one-time operation, so we cache the result
    in a global variable.
    """
    global _SYMBOL_CACHE
    if _SYMBOL_CACHE is not None:
        return _SYMBOL_CACHE

    symbol_map = {}
    for currency in pycountry.currencies:
        symbol = get_currency_symbol(currency.alpha_3, locale=locale)
        # babel sends the currency code back when it doesn't
        # find an appropriate symbol, so the below check filters
        # for such occurences.
        if symbol != currency.alpha_3:
            symbol_map[symbol] = currency.alpha_3

    _SYMBOL_CACHE = symbol_map
    return symbol_map


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
    timeout: int | None = None,
    asp=False,
    **kwargs: dict[str, Any],
) -> dict[str, Any]:
    params = _prepare_scrapfly_params(url, asp=asp, **kwargs)
    if timeout is not None:
        _timeout = timeout
    elif asp:
        # large timeout is required only when using asp.
        _timeout = config.SCRAPFLY_REQUEST_TIMEOUT
    else:
        _timeout = config.DEFAULT_HTTP_TIMEOUT

    with httpx_client(timeout=_timeout) as client:
        # https://scrapfly.io/docs/scrape-api/getting-started#spec
        response = client.get(
            SCRAPFLY_URL,
            params=params,
        )
        _raise_for_status(response)

    return response.json()["result"]["content"]


async def make_scrapfly_async_request(
    url: str,
    *,
    asp=False,
    **kwargs,
) -> dict[str, Any]:
    params = _prepare_scrapfly_params(url, asp=asp, **kwargs)
    if asp:
        # large timeout is required only when using asp.
        timeout = config.SCRAPFLY_REQUEST_TIMEOUT
    else:
        timeout = config.DEFAULT_HTTP_TIMEOUT

    async with httpx_async_client() as client:
        # https://scrapfly.io/docs/scrape-api/getting-started#spec
        response = await client.get(
            SCRAPFLY_URL,
            timeout=timeout,
            params=params,
        )
        _raise_for_status(response)

    return response.json()["result"]["content"]


def _prepare_scrapfly_params(url: str, *, asp: bool, **kwargs: Any) -> dict[str, Any]:
    params = {
        "key": config.SCRAPFLY_API_KEY,
        "url": url,
        "asp": asp,
        "debug": True,
    }
    params.update(kwargs)
    return params


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


@retry_on_http_errors(additional_status_codes=[404])
def get_exchange_rate(
    *,
    to_currency: str = config.DEFAULT_CURRENCY,
    from_currency: str,
    exchange_date: datetime | None = None,
) -> Decimal | None:
    """
    Doc: https://github.com/fawazahmed0/exchange-api?tab=readme-ov-file
    """
    if from_currency == to_currency:
        return Decimal("1")

    if exchange_date is None:
        # some portals might not provide the posted date.
        exchange_date = utcnow_naive().date()

    exchange_date_str = exchange_date.strftime("%Y-%m-%d")
    from_currency = from_currency.lower()
    to_currency = to_currency.lower()
    url = EXCHANGE_RATE_API_URL.format(date=exchange_date_str, currency=to_currency)
    with httpx_client() as client:
        try:
            response = client.get(url)
        except (
            httpx.RequestError,
            httpx.HTTPStatusError,
        ) as exc:
            logger.warning(f"Failed to fetch exchange rate from {url}: {exc}")
            fallback_url = EXCHANGE_RATE_FALLBACK_API_URL.format(
                date=exchange_date_str, currency=to_currency
            )
            response = client.get(fallback_url)

    data = response.json()
    rate = data[to_currency].get(from_currency)
    if rate:
        return Decimal(str(rate))
