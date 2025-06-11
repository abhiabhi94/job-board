import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent


# Load environment variables
env_path = ".env"
ENV = os.getenv("ENV")
if ENV == "test":
    env_path = ".test.env"

load_dotenv(env_path, override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
# default path is just provided so that the code works in local development
# in production, it should be provided as an environment variable
SERVICE_ACCOUNT_KEY_FILE_PATH = os.getenv("SERVICE_ACCOUNT_KEY_FILE", "something.json")
SERVER_EMAIL = os.getenv("SERVER_EMAIL")
SQL_DEBUG = os.getenv("SQL_DEBUG", "False").lower() == "true"
LOG_DIR = os.getenv("LOG_DIR", BASE_DIR / "logs")
# days before which we should ignore jobs
JOB_AGE_LIMIT_DAYS = int(os.getenv("JOB_AGE_LIMIT_DAYS", 90))
DEFAULT_HTTP_TIMEOUT = int(os.getenv("DEFAULT_HTTP_TIMEOUT", 30))
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "USD")
DEFAULT_LOCALE = os.getenv("DEFAULT_LOCALE", "en_US")

SCRAPFLY_API_KEY = os.getenv("SCRAPFLY_API_KEY")
SCRAPFLY_REQUEST_TIMEOUT = int(os.getenv("SCRAPFLY_REQUEST_TIMEOUT", 500))  # seconds

WORK_AT_A_STARTUP_COOKIE = os.getenv("WORK_AT_A_STARTUP_COOKIE")
WORK_AT_A_STARTUP_CSRF_TOKEN = os.getenv("WORK_AT_A_STARTUP_CSRF_TOKEN")
