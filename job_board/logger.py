import logging

from job_board import config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%z %m/%d/%Y %I:%M:%S %p",
    level=config.LOG_LEVEL.upper(),
    encoding="utf-8",
    handlers=[
        logging.FileHandler("job-board.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("job-board")
job_rejected_logger = logging.getLogger("job-rejected")
