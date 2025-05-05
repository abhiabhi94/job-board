from datetime import datetime
from datetime import timedelta
from datetime import timezone
from unittest import mock

import httpx
import pytest
from freezegun import freeze_time

from job_board.utils import parse_relative_time
from job_board.utils import retry_on_http_errors

# Fixed datetime for consistent testing
FIXED_NOW = datetime(2025, 3, 13, 12, 0, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "relative_str, expected_delta",
    [
        # None input
        (None, None),
        # days with singular and plural forms
        ("1 day ago", timedelta(days=1)),
        ("5 days ago", timedelta(days=5)),
        # hours with singular and plural forms
        ("1 hour ago", timedelta(hours=1)),
        ("12 hours ago", timedelta(hours=12)),
        # minutes with singular and plural forms
        ("1 minute ago", timedelta(minutes=1)),
        ("30 minutes ago", timedelta(minutes=30)),
        # seconds with singular and plural forms
        ("1 second ago", timedelta(seconds=1)),
        ("45 seconds ago", timedelta(seconds=45)),
        # months with singular and plural forms
        ("1 month ago", timedelta(days=30)),
        ("3 months ago", timedelta(days=90)),
    ],
)
@freeze_time(FIXED_NOW)
def test_parse_relative_time_valid_inputs(relative_str, expected_delta):
    result = parse_relative_time(relative_str)
    if expected_delta is None:
        assert result is expected_delta
    else:
        expected = FIXED_NOW - expected_delta

        assert result == expected
        assert result.tzinfo == timezone.utc


@pytest.mark.parametrize(
    "relative_str, expected_error_msg",
    [
        ("1 year ago", "Unsupported time unit: year"),
        ("2 weeks ago", "Unsupported time unit: weeks"),
    ],
)
def test_parse_relative_time_unsupported_units(relative_str, expected_error_msg):
    with pytest.raises(ValueError) as excinfo:
        parse_relative_time(relative_str)

    assert str(excinfo.value) == expected_error_msg


def test_parse_relative_time_uses_current_time():
    # Use two different fixed times to verify the function uses datetime.now()
    with freeze_time("2025-01-01 00:00:00+00:00"):
        time_1 = parse_relative_time("1 day ago")

    with freeze_time("2025-02-01 00:00:00+00:00"):
        time_2 = parse_relative_time("1 day ago")

    # The two results should differ by exactly 31 days
    assert (time_2 - time_1) == timedelta(days=31)


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
