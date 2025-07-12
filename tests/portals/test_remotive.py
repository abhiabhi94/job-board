from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal

import httpx
import pytest
from freezegun import freeze_time

from job_board.portals import Remotive
from job_board.portals.remotive import DATE_FORMAT


@pytest.fixture
def frozen_time():
    now = datetime.now(timezone.utc)
    with freeze_time(now):
        yield now.strftime(DATE_FORMAT)


@pytest.fixture
def sample_job(frozen_time):
    return {
        "url": "https://remotive.com/jobs/123",
        "title": "Python Developer",
        "description": (
            "<p>We are looking for a Python developer with 3+ years of experience.</p>"
        ),
        "candidate_required_location": "Worldwide",
        "tags": ["python", "django", "api"],
        "salary": "90000-120000",
        "publication_date": frozen_time,
    }


@pytest.fixture
def sample_jobs_response(sample_job, frozen_time):
    return {
        "jobs": [
            sample_job,
            # no matching keywords
            {
                "url": "https://remotive.com/jobs/124",
                "title": "Java Developer",
                "description": "<p>We are looking for a Java developer.</p>",
                "candidate_required_location": "Worldwide",
                "tags": ["java", "spring"],
                "salary": "100000-130000",
                "publication_date": frozen_time,
            },
            # matching keywords but low salary
            {
                "url": "https://remotive.com/jobs/125",
                "title": "Junior Python Developer",
                "description": "<p>Entry level position.</p>",
                "candidate_required_location": "Worldwide",
                "tags": ["python"],
                "salary": "40000-50000",
                "publication_date": frozen_time,
            },
            # no salary info
            {
                "url": "https://remotive.com/jobs/126",
                "title": "Python Developer",
                "description": "<p>We need a Python expert.</p>",
                "candidate_required_location": "Worldwide",
                "tags": ["python"],
                "publication_date": frozen_time,
            },
            # too old
            {
                "url": "https://remotive.com/jobs/127",
                "title": "Python Developer",
                "description": "<p>We need a Python expert.</p>",
                "candidate_required_location": "Worldwide",
                "tags": ["python"],
                "salary": "90000-120000",
                "publication_date": (
                    datetime.now(timezone.utc) - timedelta(days=30)
                ).strftime(DATE_FORMAT),
            },
        ]
    }


def test_fetch_jobs(
    respx_mock,
    sample_jobs_response,
    frozen_time,
    db_session,
):
    respx_mock.get(Remotive.url).mock(
        return_value=httpx.Response(json=sample_jobs_response, status_code=200)
    )

    portal = Remotive()

    jobs = portal.fetch_jobs()

    assert len(jobs) == 5
    job = jobs[0]

    assert job.title == "Python Developer"
    assert job.link == "https://remotive.com/jobs/123"
    assert job.description is not None
    assert job.min_salary == Decimal("90000.00")
    assert job.max_salary == Decimal("120000.00")
    assert job.posted_on == datetime.strptime(frozen_time, DATE_FORMAT).astimezone(
        timezone.utc
    )
    assert job.locations == ["Worldwide"]
    assert job.is_remote is True
    assert job.tags == ["python", "django", "api"]
