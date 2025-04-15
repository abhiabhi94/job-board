from datetime import datetime, timezone
import itertools

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy import Boolean
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, update, func, Index
from sqlalchemy.sql import expression


from job_board.logger import logger
from job_board.connection import get_session
from job_board.notifier.mail import get_email_provider
from job_board import config
from job_board.base import Job as JobListing
from job_board.utils import jinja_env


# Base class for all models
class BaseModel(DeclarativeBase):
    pass


class Job(BaseModel):
    __tablename__ = "job"

    id = Column(Integer, primary_key=True, autoincrement=True)
    link = Column(String, nullable=False)
    title = Column(String, nullable=False)
    salary = Column(Numeric, nullable=False)
    posted_on = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        server_default=func.now(),
    )
    notified = Column(Boolean, default=False, server_default=expression.false())

    __table_args__ = (
        Index(
            "ix_job_link_lower",
            func.lower(link),
            unique=True,
        ),
    )


def store_jobs(jobs: JobListing):
    if not jobs:
        logger.debug("No jobs to store")
        return

    values = []
    for job in jobs:
        value = {
            "link": job.link,
            "title": job.title,
            "salary": job.salary,
        }
        if posted_on := job.posted_on:
            value["posted_on"] = posted_on
        values.append(value)

    insert_statement = insert(Job).values(values).returning(Job.id)
    session = get_session()
    with session.begin():
        statement = insert_statement.on_conflict_do_nothing(
            index_elements=[
                func.lower(Job.link),
            ],
        )
        job_ids = session.execute(statement).scalars().all()

    logger.debug(f"Stored {len(job_ids)} new jobs successfully")
    return job_ids


def notify(job_ids: list[int]):
    if not job_ids:
        logger.info("No jobs to notify")
        return

    statement = (
        select(Job)
        .where(Job.notified.is_(False) & Job.id.in_(job_ids))
        .order_by(Job.posted_on.desc(), Job.salary.desc())
    )
    session = get_session()
    with session.begin():
        jobs = session.execute(statement).scalars().all()
        if not jobs:
            logger.info("No new jobs found for notification")
            return

        job_listings_by_id = {
            job.id: JobListing(
                title=job.title,
                link=job.link,
                salary=job.salary,
                posted_on=job.posted_on,
            )
            for job in jobs
        }

    for batched_ids in itertools.batched(job_listings_by_id, config.MAX_JOBS_PER_EMAIL):
        batched_listings = [job_listings_by_id[job_id] for job_id in batched_ids]
        _notify(batched_listings)
        # update `notified` flag after notified with email.
        statement = (
            update(Job)
            .where(Job.notified.is_(False), Job.id.in_(batched_ids))
            .values(notified=True)
        )
        session = get_session()
        with session.begin():
            session.execute(statement)


def _notify(job_listings: list[JobListing]):
    template = jinja_env.get_template("mail.html")
    today = datetime.today().strftime("%B %d, %Y")
    subject = f"Jobs To Apply | {today}"
    email_provider = get_email_provider()

    email_body = template.render(
        jobs=job_listings,
        subject=subject,
    )
    logger.debug(f"Email to send:::\n{email_body}")

    email_provider.send_email(
        sender=config.SERVER_EMAIL,
        receivers=config.RECIPIENTS,
        subject=subject,
        body=email_body,
    )
    logger.info(f"{len(job_listings)} jobs sent successfully")
