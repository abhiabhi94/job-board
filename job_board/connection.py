from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from job_board import config

_engine = None
_SessionFactory = None
_test_session = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            config.DATABASE_URL,
            echo=config.SQL_DEBUG,
        )

    return _engine


def _get_session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(
            bind=get_engine(),
            future=True,
        )
    return _SessionFactory


def get_session(*, readonly=True):
    global _test_session
    if _test_session:
        if not config.TEST_ENV:
            raise RuntimeError("Please use the test environment to run tests. ")
        return _test_session

    Session = _get_session_factory()
    session = Session()
    if readonly:
        session.execute(text("SET TRANSACTION READ ONLY"))
    return session
