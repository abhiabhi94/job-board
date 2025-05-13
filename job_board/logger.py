import logging.handlers
import os

from job_board import config

log_dir = config.LOG_DIR
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, "app.log")

rotating_handler = logging.handlers.RotatingFileHandler(
    filename=log_file,
    maxBytes=10 * 1024 * 1024,  # 10MB per file
    backupCount=5,  # Keep 5 backup files
    encoding="utf-8",
)

console_handler = logging.StreamHandler()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%z %d/%m/%Y %I:%M:%S %p",
    level=config.LOG_LEVEL.upper(),
    encoding="utf-8",
    handlers=[
        console_handler,
        rotating_handler,
    ],
)
logger = logging.getLogger("job-board")
logger.info(f"logging to file: {log_file}")
