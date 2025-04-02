# TODO: move these to a config file
import os
from pathlib import Path
from decimal import Decimal

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent


# Load environment variables
env_path = ".env"
if os.getenv("TEST_ENV") == "true":
    env_path = ".test.env"

load_dotenv(env_path, override=True)

KEYWORDS = [
    keyword.strip() for keyword in os.getenv("KEYWORDS", "").split(",") if keyword
]
REGION = os.getenv("REGION")
SALARY = Decimal(os.environ.get("SALARY", str(60_000)))
CURRENCY_SALARY = os.environ.get("CURRENCY_SALARY")
RECEIPIENTS = [
    receipient.strip()
    for receipient in os.getenv("RECEIPIENTS", "").split(",")
    if receipient
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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPEN_AI_MODEL = "gpt-4o"
WELLFOUND_APOLLO_SIGNATURE = os.getenv("WELLFOUND_APOLLO_SIGNATURE")
WELLFOUND_COOKIE = os.getenv("WELLFOUND_COOKIE")
WELLFOUND_DATADOME_COOKIE = os.getenv("WELLFOUND_DATADOME_COOKIE")
