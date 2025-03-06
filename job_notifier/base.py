from typing import NamedTuple
from datetime import datetime, timezone, timedelta


class Message(NamedTuple):
    title: str
    salary: str
    link: str
    # some websites don't provide the date of posting
    # but directly provide the time passed since posting
    # for example: posted 5 days ago.
    posted_on: datetime | str | None = None

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

        return f"""
        Title: {self.title}
        Salary: {self.salary:,}
        Link: {self.link}
        Posted: {posted_on}
        """
