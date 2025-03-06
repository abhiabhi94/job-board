from job_notifier.portals import (
    weworkremotely,
)
from job_notifier.logger import logger


def main():
    return weworkremotely.WeWorkRemotely().get_messages_to_notify()


if __name__ == "__main__":
    exit(logger.info(main()))
