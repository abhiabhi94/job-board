from job_notifier.portals import (
    weworkremotely,
)


def main():
    return weworkremotely.WeWorkRemotely().get_messages_to_notify()


if __name__ == "__main__":
    exit(main())
