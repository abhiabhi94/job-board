from job_board.connection import get_engine
from job_board.logger import logger
from job_board.models import BaseModel


def init_db():
    """
    Initialize the database by creating all tables and setting up initial data.
    """
    logger.info("Creating Tables")
    engine = get_engine()
    BaseModel.metadata.create_all(bind=engine)
