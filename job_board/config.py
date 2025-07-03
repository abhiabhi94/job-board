import os
from pathlib import Path

import sentry_sdk
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
DEFAULT_CURRENCY_FRACTION_DIGITS = int(os.getenv("DEFAULT_CURRENCY_FRACTION_DIGITS", 2))
DEFAULT_LOCALE = os.getenv("DEFAULT_LOCALE", "en_US")

SCRAPFLY_API_KEY = os.getenv("SCRAPFLY_API_KEY")
SCRAPFLY_REQUEST_TIMEOUT = int(os.getenv("SCRAPFLY_REQUEST_TIMEOUT", 500))  # seconds

WORK_AT_A_STARTUP_COOKIE = os.getenv("WORK_AT_A_STARTUP_COOKIE")
WORK_AT_A_STARTUP_CSRF_TOKEN = os.getenv("WORK_AT_A_STARTUP_CSRF_TOKEN")
# the current scrapfly plan allows only 5 concurrent requests.
WELLFOUND_REQUESTS_BATCH_SIZE = int(os.getenv("WELLFOUND_REQUESTS_BATCH_SIZE", 5))
HIMALAYAS_REQUESTS_BATCH_SIZE = int(os.getenv("HIMALAYAS_REQUESTS_BATCH_SIZE", 10))

# Sentry configuration
SENTRY_DSN = os.getenv("SENTRY_DSN")
if ENV != "dev":
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=ENV,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
    )
