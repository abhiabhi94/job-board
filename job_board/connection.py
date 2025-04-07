from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from job_board import config

_engine = None
_SessionFactory = None


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
        _SessionFactory = sessionmaker(bind=get_engine())
    return _SessionFactory


def get_session():
    Session = _get_session_factory()
    return Session()
