import contextlib
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import Session
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
            expire_on_commit=False,
        )
    return _SessionFactory


@contextlib.contextmanager
def get_session(*, readonly=True) -> Generator[Session, None, None]:
    global _test_session
    if _test_session:
        if not config.TEST_ENV:
            raise RuntimeError("Please use the test environment to run tests. ")
        yield _test_session

        return None

    Session = _get_session_factory()
    with Session() as session:
        with session.begin():
            if readonly:
                session.execute(text("SET TRANSACTION READ ONLY"))

            yield session
