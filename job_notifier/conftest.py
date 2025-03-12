import os


def pytest_configure():
    os.environ["TEST_ENV"] = "true"
