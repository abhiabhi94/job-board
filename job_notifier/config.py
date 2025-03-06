# TODO: move these to a config file
import os

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
