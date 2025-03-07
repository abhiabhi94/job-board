from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Numeric
from sqlalchemy import Boolean
from job_notifier.config import DATABASE_URL
from datetime import datetime, timezone, timedelta
import markdown

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

# Base class for models
Base = declarative_base()


# Define the Job model
class Job(Base):
    __tablename__ = "job"

    id = Column(Integer, primary_key=True, autoincrement=True)
    link = Column(String, unique=True, nullable=False)
    # message = Column(JSON, nullable=False)
    title = Column(String, nullable=False)
    salary = Column(Numeric, nullable=False)
    posted_on = Column(String)  # not all platform provide structured datetime

    notified = Column(Boolean, default=False)

    def __repr__(self) -> str:
        if isinstance(self.posted_on, datetime):
            difference = datetime.now(timezone.utc) - self.posted_on
            if difference > timedelta(days=1):
                posted_on = f"{difference.days} days ago"
            else:
                hours = difference.seconds // 3600
                posted_on = f"{hours} hours ago"
        else:
            posted_on = self.posted_on

        return markdown.markdown(f"""
        ### Title: {self.title}
        **Salary: ${self.salary:,}**
        Link: {self.link}
        Posted: {posted_on}
        """)


# Create a session
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()


if __name__ == "__main__":
    # Create tables in the database
    Base.metadata.create_all(engine)
