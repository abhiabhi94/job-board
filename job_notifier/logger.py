import logging

from job_notifier import config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%z %m/%d/%Y %I:%M:%S %p",
    level=config.LOG_LEVEL.upper(),
    encoding="utf-8",
    filename="job-notifier.log",
)
logger = logging.getLogger("job-notifier")
