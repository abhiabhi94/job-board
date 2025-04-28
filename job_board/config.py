import os
from pathlib import Path
from decimal import Decimal

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent


# Load environment variables
env_path = ".env"
TEST_ENV = os.getenv("TEST_ENV") == "true"
if TEST_ENV:
    env_path = ".test.env"

load_dotenv(env_path, override=True)

KEYWORDS = [
    keyword.strip() for keyword in os.getenv("KEYWORDS", "").split(",") if keyword
]
REGION = os.getenv("REGION")
SALARY = Decimal(os.environ.get("SALARY", str(60_000)))
CURRENCY_SALARY = os.environ.get("CURRENCY_SALARY")
RECIPIENTS = [
    recipient.strip()
    for recipient in os.getenv("RECIPIENTS", "").split(",")
    if recipient
]
NATIVE_COUNTRY = os.getenv("NATIVE_COUNTRY", "").strip()
PREFERRED_CITIES = [
    city.strip() for city in os.getenv("PREFERRED_CITIES", "").split(", ") if city
]

DATABASE_URL = os.getenv("DATABASE_URL")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
# default path is just provided so that the code works in local development
# in production, it should be provided as an environment variable
SERVICE_ACCOUNT_KEY_FILE_PATH = BASE_DIR / os.getenv(
    "SERVICE_ACCOUNT_KEY_FILE", "something.json"
)
SERVER_EMAIL = os.getenv("SERVER_EMAIL")
SQL_DEBUG = os.getenv("SQL_DEBUG", "False").lower() == "true"
# days before which we should ignore jobs
JOB_AGE_LIMIT_DAYS = int(os.getenv("JOB_AGE_LIMIT_DAYS", 90))
DEFAULT_HTTP_TIMEOUT = int(os.getenv("DEFAULT_HTTP_TIMEOUT", 30))
MAX_JOBS_PER_EMAIL = int(os.getenv("MAX_JOBS_PER_EMAIL", 10))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPEN_AI_MODEL = "gpt-4o"
SCRAPFLY_API_KEY = os.getenv("SCRAPFLY_API_KEY")
SCRAPFLY_REQUEST_TIMEOUT = int(os.getenv("SCRAPFLY_REQUEST_TIMEOUT", 500))  # seconds

WORK_AT_A_STARTUP_COOKIE = os.getenv("WORK_AT_A_STARTUP_COOKIE")
WORK_AT_A_STARTUP_CSRF_TOKEN = os.getenv("WORK_AT_A_STARTUP_CSRF_TOKEN")
