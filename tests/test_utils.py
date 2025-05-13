from datetime import datetime
from decimal import Decimal
from unittest import mock

import httpx
import pytest
from freezegun import freeze_time

from job_board.utils import EXCHANGE_RATE_API_URL
from job_board.utils import EXCHANGE_RATE_FALLBACK_API_URL
from job_board.utils import get_exchange_rate
from job_board.utils import retry_on_http_errors


def test_retrying_with_errors(respx_mock):
    url = "https://example.com"

    @retry_on_http_errors()
    def foo():
        return httpx.get(url)

    respx_mock.get(url).mock(
        side_effect=[
            httpx.TimeoutException,  # http error retried.
            ValueError,  # non-http error re-raised.
        ]
    )
    with mock.patch("tenacity.nap.time.sleep") as mocked_sleep:
        with pytest.raises(ValueError):
            foo()

    mocked_sleep.assert_called_once()


today = datetime.today()


@freeze_time(today)
def test_get_exchange_rate(respx_mock):
    assert get_exchange_rate(
        from_currency="usd",
        to_currency="usd",
        exchange_date=today,
    ) == Decimal("1")

    today_str = today.strftime("%Y-%m-%d")
    valid_response = httpx.Response(
        status_code=200,
        json={
            "date": today_str,
            "usd": {
                "inr": 82.899,
            },
        },
    )
    error_response = httpx.Response(
        status_code=404,
        json={"error": "Not found"},
    )
    url = EXCHANGE_RATE_API_URL.format(
        date=today_str,
        currency="usd",
    )

    respx_mock.get(url).mock(return_value=valid_response)

    rate = get_exchange_rate(
        from_currency="inr",
        to_currency="usd",
        exchange_date=today,
    )
    assert rate == Decimal("82.899")

    # verify for the fallback URL
    respx_mock.get(url).mock(return_value=error_response)
    fallback_url = EXCHANGE_RATE_FALLBACK_API_URL.format(
        date=today_str,
        currency="usd",
    )
    respx_mock.get(fallback_url).mock(return_value=valid_response)

    rate = get_exchange_rate(
        from_currency="inr",
        to_currency="usd",
    )
    assert rate == Decimal("82.899")

    # verify retry on error
    respx_mock.get(url).mock(side_effect=[error_response, valid_response])
    respx_mock.get(fallback_url).mock(return_value=error_response)

    with mock.patch("tenacity.nap.time.sleep") as mocked_sleep:
        rate = get_exchange_rate(
            from_currency="inr",
            to_currency="usd",
        )

    mocked_sleep.assert_called_once()

    assert rate == Decimal("82.899")

    # rate not found
    respx_mock.get(url).mock(
        return_value=httpx.Response(
            status_code=200,
            json={
                "usd": {},
            },
        )
    )
    assert (
        get_exchange_rate(
            from_currency="inr",
            to_currency="usd",
            exchange_date=today,
        )
        is None
    )


def test_get_exchange_rate_api_not_working(respx_mock):
    today_str = today.strftime("%Y-%m-%d")
    url = EXCHANGE_RATE_API_URL.format(
        date=today_str,
        currency="usd",
    )
    respx_mock.get(url).mock(
        return_value=httpx.Response(
            status_code=500,
            json={"error": "Internal Server Error"},
        )
    )
    fallback_url = EXCHANGE_RATE_FALLBACK_API_URL.format(
        date=today_str,
        currency="usd",
    )
    respx_mock.get(fallback_url).mock(
        return_value=httpx.Response(
            status_code=500,
            json={"error": "Internal Server Error"},
        )
    )

    with mock.patch("tenacity.nap.time.sleep") as mocked_sleep:
        assert (
            get_exchange_rate(
                from_currency="inr",
                to_currency="usd",
                exchange_date=today,
            )
            is None
        )

    mocked_sleep.assert_called()
