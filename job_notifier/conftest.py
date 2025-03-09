import os


def pytest_configure():
    os.environ.setdefault("SERVICE_ACCOUNT_KEY_FILE", "test.json")
    os.environ.setdefault("RECEIPIENTS", "rec_test1@gmail.com,rec_test2@gmail.com")
    os.environ.setdefault("SERVER_EMAIL", "server_test@gmail.com")
