from datetime import datetime
from decimal import Decimal
from unittest import mock

import httpx
import pytest
from freezegun import freeze_time
from pydantic import BaseModel

from job_board import config
from job_board.utils import EXCHANGE_RATE_API_URL
from job_board.utils import EXCHANGE_RATE_FALLBACK_API_URL
from job_board.utils import get_exchange_rate
from job_board.utils import get_openai_schema
from job_board.utils import log_to_sentry
from job_board.utils import make_scrapfly_request
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


def test_make_scrapfly_request_timeout():
    with (
        mock.patch("job_board.utils.http_client") as mock_client,
    ):
        make_scrapfly_request("https://example.com", timeout=100)

    mock_client.assert_called_once()
    assert mock_client.call_args.kwargs["timeout"] == 100


def test_log_to_sentry():
    with mock.patch("job_board.utils.sentry_sdk") as mock_sentry_sdk:
        log_to_sentry(
            Exception("Test exception"),
            "webserver",
            tags={"key": "value"},
        )

    mock_sentry_sdk.capture_exception.assert_called_once()

    with (
        mock.patch.object(config, "ENV", "dev"),
        mock.patch("job_board.utils.sentry_sdk") as mock_sentry_sdk,
    ):
        log_to_sentry(
            Exception("Test exception"),
            "scheduler",
            tags={"key": "value"},
        )

    mock_sentry_sdk.capture_exception.assert_not_called()


def test_get_openai_schema():
    class TestModel(BaseModel):
        title: str
        description: str | None = None
        tags: list[str] = []

    class ListTestModel(BaseModel):
        items: list[TestModel]

    schema = get_openai_schema(ListTestModel)

    expected_schema = {
        "$defs": {
            "TestModel": {
                "additionalProperties": False,
                "properties": {
                    "description": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                        "default": None,
                        "title": "Description",
                    },
                    "tags": {
                        "default": [],
                        "items": {"type": "string"},
                        "title": "Tags",
                        "type": "array",
                    },
                    "title": {"title": "Title", "type": "string"},
                },
                "required": ["title"],
                "title": "TestModel",
                "type": "object",
            }
        },
        "additionalProperties": False,
        "properties": {
            "items": {
                "items": {"$ref": "#/$defs/TestModel"},
                "title": "Items",
                "type": "array",
            }
        },
        "required": ["items"],
        "title": "ListTestModel",
        "type": "object",
    }

    assert schema == expected_schema
