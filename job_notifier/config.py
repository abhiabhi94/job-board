# TODO: move these to a config file
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent


# Load environment variables
env_path = None
if os.getenv("TEST_ENV") == "true":
    env_path = ".test.env"
else:
    env_path = ".env"

load_dotenv(env_path, override=True)

DATABASE_URL = os.getenv("DATABASE_URL")

KEYWORDS = {
    "python",
    "django",
    "flask",
    "fastapi",
    "sqlalchemy",
    "back-end",
    "backend",
}

REGION = "remote"
SALARY = 60_000  # in USD
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
# default path is just provided so that the code works in local development
# in production, it should be provided as an environment variable
SERVICE_ACCOUNT_KEY_FILE_PATH = BASE_DIR / os.getenv(
    "SERVICE_ACCOUNT_KEY_FILE", "something.json"
)
SERVER_EMAIL = os.getenv("SERVER_EMAIL")
RECEIPIENTS = os.getenv("RECEIPIENTS", "").split(",")
SQL_DEBUG = os.getenv("SQL_DEBUG", "False").lower() == "true"
