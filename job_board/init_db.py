from job_board.models import BaseModel
from job_board.portals.models import PortalSetting
from job_board.logger import logger
from job_board.connection import get_engine


def init_db():
    """
    Initialize the database by creating all tables and setting up initial data.
    """
    logger.info("Creating Tables")
    engine = get_engine()
    BaseModel.metadata.create_all(bind=engine)
    PortalSetting.create_portal_setting()
