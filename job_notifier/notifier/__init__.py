from job_notifier.notifier.mail import EmailProvider
from job_notifier.logger import logger
from job_notifier.models import session, Job
from job_notifier import config
from sqlalchemy import update


def notify():
    jobs = session.query(Job).filter_by(notified=False).all()
    logger.debug(f"number of jobs:::{len(jobs)}")

    if not len(jobs):
        logger.info("No new jobs found for notification!")
        return

    # TODO - send email in batches..
    # add constraints in number of jobs to send in one mail

    email_provider = EmailProvider()
    sender_email = config.SERVER_EMAIL

    email_subject = "Dream Jobs"
    email_body = ""
    for job in jobs:
        email_body += f"{str(job)} \n\n"

    logger.debug(f"message:::{email_body}")

    try:
        for to_email in config.RECEIPIENTS:
            email_provider.send_email(sender_email, to_email, email_subject, email_body)

    except Exception as error:
        logger.debug(f"Error occured in sending message:: {error}")
        return

    logger.debug("jobs sent successfully")

    # update `notified` flag after notified with email.
    stmt = update(Job).where(Job.notified.is_(False)).values(notified=True)
    session.execute(stmt)
    session.commit()

    logger.debug("flag updated successfully")


if __name__ == "__main__":
    exit(logger.info(notify()))
