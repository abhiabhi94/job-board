# TODO: move these to a config file
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"  # Convert to boolean


BASE_DIR = Path(__file__).parent.parent

keywords = {
    "python",
    "django",
    "flask",
    "fastapi",
    "sqlalchemy",
    "back-end",
    "backend",
}
region = "remote"
salary = 60_000  # in USD
log_level = os.environ.get("LOG_LEVEL", "DEBUG")
SERVICE_ACCOUNT_KEY_FILE_PATH = BASE_DIR / os.getenv("SERVICE_ACCOUNT_KEY_FILE")
SERVER_EMAIL = os.getenv("SERVER_EMAIL")
RECEIPIENTS = os.getenv("RECEIPIENTS", []).split(",")
