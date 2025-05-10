import logging

from job_board import config

log_file = "job-board-test.log" if config.TEST_ENV else "job-board.log"
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%z %d/%m/%Y %I:%M:%S %p",
    level=config.LOG_LEVEL.upper(),
    encoding="utf-8",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("job-board")
job_rejected_logger = logger.getChild("job-rejected")
