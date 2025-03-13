import logging

from job_notifier import config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%z %m/%d/%Y %I:%M:%S %p",
    level=config.LOG_LEVEL.upper(),
    encoding="utf-8",
    handlers=[
        logging.FileHandler("job-notifier.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("job-notifier")
