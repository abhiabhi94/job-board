from job_notifier.portals import (
    weworkremotely,
)
from job_notifier.logger import logger
from models import session, Job
import schedule
import time
from job_notifier.notifier import notify
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime


def store_jobs(messages):
    for message in messages:
        stmt = (
            insert(Job)
            .values(
                link=message.link,
                title=message.title,
                salary=message.salary,
                posted_on=message.posted_on,
            )
            .on_conflict_do_nothing(index_elements=["link"])
        )
        # Ignore if `link` already exists

        session.execute(stmt)
        session.commit()

    logger.debug(f"Stored {len(messages)} new jobs successfully")


def main():
    logger.debug(f"********Job started:{datetime.now()}**********")
    messages = weworkremotely.WeWorkRemotely().get_messages_to_notify()
    store_jobs(messages)
    notify()
    logger.debug(f"********Job completed:{datetime.now()}**********")


# schedule.every(1).minutes.do(main) # for testing script
schedule.every().day.at("10:30").do(main)

while True:
    schedule.run_pending()
    time.sleep(1)
