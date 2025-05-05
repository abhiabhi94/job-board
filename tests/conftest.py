import importlib
import os

import pytest
from sqlalchemy.orm import sessionmaker

import job_board.connection as connection_module
from job_board import config
from job_board.connection import _test_session
from job_board.connection import get_engine
from job_board.init_db import init_db
from job_board.models import BaseModel


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


@pytest.fixture(scope="session")
def db_setup():
    init_db()
    yield
    engine = get_engine()
    BaseModel.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_setup):
    """
    Returns a sqlalchemy session, and after the test, it tears down
    everything properly.
    """
    engine = get_engine()
    # ensure the database URL is set correctly
    # for testing, otherwise it will end up using
    # the local/production database
    assert "tester" in str(engine.url)
    connection = engine.connect()
    # begin the nested transaction
    transaction = connection.begin()

    TestSession = sessionmaker(bind=connection, future=True)
    session = TestSession()
    # This is just a hack to make sure that the session
    # for the test is same as the one in this fixture.
    # TODO: find a better way to do this
    connection_module._test_session = session
    yield session
    connection_module._test_session = _test_session

    session.close()
    # roll back the broader transaction
    transaction.rollback()
    # put back the connection to the connection pool
    connection.close()
