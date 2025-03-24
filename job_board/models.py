from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy import Boolean
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, update
from jinja2 import Environment, FileSystemLoader
import pathlib

from job_board.logger import logger
from job_board.connection import Session, engine
from job_board.notifier.mail import EmailProvider
from job_board import config
from job_board.base import Job as JobListing

jinja_env = Environment(
    loader=FileSystemLoader(pathlib.Path(__file__).parent / "templates"),
)


# Base class for all models
class Base(DeclarativeBase):
    pass


def create_tables():
    logger.debug("Creating tables")
    Base.metadata.create_all(bind=engine)


class Job(Base):
    __tablename__ = "job"

    id = Column(Integer, primary_key=True, autoincrement=True)
    link = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    salary = Column(Numeric, nullable=False)
    posted_on = Column(DateTime)
    notified = Column(Boolean, default=False)


def store_jobs(jobs: JobListing):
    if not jobs:
        logger.debug("No jobs to store")
        return

    insert_statement = (
        insert(Job)
        .values(
            [
                {
                    "link": job.link,
                    "title": job.title,
                    "salary": job.salary,
                    "posted_on": job.posted_on,
                }
                for job in jobs
            ],
        )
        .returning(Job.id)
    )
    with Session.begin() as session:
        statement = insert_statement.on_conflict_do_nothing(index_elements=[Job.link])
        job_ids = session.execute(statement).scalars().all()

    logger.debug(f"Stored {len(job_ids)} new jobs successfully")


def notify():
    job_ids = []
    statement = select(Job).where(Job.notified.is_(False))
    template = jinja_env.get_template("mail.html")
    subject = "Jobs To Apply"

    with Session.begin() as session:
        jobs = session.execute(statement).scalars().all()
        job_ids = [job.id for job in jobs]
        job_listings = [
            JobListing(
                link=job.link,
                title=job.title,
                salary=job.salary,
                posted_on=job.posted_on,
            )
            for job in jobs
        ]

    email_body = template.render(
        jobs=job_listings,
        subject=subject,
    )

    logger.debug(f"Number of jobs to send:::{len(job_ids)}")
    if not len(job_ids):
        logger.info("No new jobs found for notification!")
        return

    # TODO - send email in batches..
    # add constraints in number of jobs to send in one mail
    email_provider = EmailProvider()

    logger.debug(f"Email to send:::\n{email_body}")

    email_provider.send_email(
        sender=config.SERVER_EMAIL,
        receivers=config.RECEIPIENTS,
        subject=subject,
        body=email_body,
    )

    logger.debug("jobs sent successfully")

    # update `notified` flag after notified with email.
    statement = (
        update(Job)
        .where(Job.notified.is_(False), Job.id.in_(job_ids))
        .values(notified=True)
    )
    with Session.begin() as session:
        session.execute(statement)

    logger.debug("notified flag updated successfully")
