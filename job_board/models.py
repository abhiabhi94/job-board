from datetime import datetime, timezone
import itertools
import uuid

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy import Boolean
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, func, Index
from sqlalchemy.sql import expression


from job_board.logger import logger
from job_board.connection import get_session
from job_board.notifier.mail import EmailProvider
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


def notify():
    statement = (
        select(Job)
        .where(Job.notified.is_(False))
        .order_by(Job.salary.desc(), Job.posted_on.desc())
    )
    session = get_session()
    with session.begin():
        jobs = session.execute(statement).scalars().all()
        if not jobs:
            logger.info("No new jobs found for notification")
            return

        job_listings_by_id = {}
        for job in jobs:
            job_listings_by_id[job.id] = JobListing(
                link=job.link,
                title=job.title,
                salary=job.salary,
                posted_on=job.posted_on,
            )

    template = jinja_env.get_template("mail.html")
    today = datetime.today().strftime("%B %d, %Y")
    subject = f"Jobs To Apply | {today}"
    email_provider = EmailProvider()

    message_id = str(uuid.uuid4())
    message_ids = [message_id]
    for batched_ids in itertools.batched(
        job_listings_by_id,
        config.MAX_JOBS_PER_EMAIL,
    ):
        batched_listings = [job_listings_by_id[job_id] for job_id in batched_ids]

        email_body = template.render(
            jobs=batched_listings,
            subject=subject,
        )

        message = email_provider.send_email(
            sender=config.SERVER_EMAIL,
            receivers=config.RECIPIENTS,
            subject=subject,
            body=email_body,
            references=message_ids,
            thread_id=message_id,
        )
        logger.info(f"{len(batched_ids)} jobs sent successfully")
        message_id = message["id"]
        message_ids.append(message_id)

        # update `notified` flag after notified with email.
        # statement = (
        #     update(Job)
        #     .where(Job.notified.is_(False), Job.id.in_(batched_ids))
        #     .values(notified=True)
        # )
        # session = get_session()
        # with session.begin():
        #     session.execute(statement)
