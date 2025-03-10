from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from job_notifier import config

engine = create_engine(
    config.DATABASE_URL,
    # used for logging SQL queries
    echo=config.SQL_DEBUG,
)

Session = sessionmaker(bind=engine)
