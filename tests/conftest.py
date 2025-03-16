import os

import pytest


def pytest_configure():
    os.environ["TEST_ENV"] = "true"


@pytest.fixture(autouse=True)
def disable_real_http_requests(respx_mock):
    yield
