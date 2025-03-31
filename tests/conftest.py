import os
import importlib

import pytest

from job_board import config


def pytest_configure():
    os.environ["TEST_ENV"] = "true"
    # reload the config module to apply
    # the test environment variables
    importlib.reload(config)


@pytest.fixture(autouse=True)
def disable_real_http_requests(respx_mock):
    yield


@pytest.fixture
def load_response():
    def _load_response(file_path: str) -> str:
        base_path = config.BASE_DIR / "tests" / "portals" / "responses"
        with open(base_path / file_path) as fp:
            return fp.read()

    return _load_response
