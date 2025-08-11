from datetime import timedelta
from decimal import Decimal
from typing import NamedTuple
from unittest.mock import patch

import pytest
from flask import template_rendered
from freezegun import freeze_time

from job_board import config
from job_board.models import store_jobs
from job_board.portals.parser import Job as JobListing
from job_board.utils import utcnow_naive
from job_board.views import (
    app as flask_app,
)
from job_board.views import AVAILABLE_TAGS
from job_board.views import PER_PAGE

now = utcnow_naive()


@pytest.fixture
def app():
    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


@pytest.fixture
def captured_templates(app):
    """Doc: https://flask.palletsprojects.com/en/stable/signals/#subscribing-to-signals"""

    class TemplateContent(NamedTuple):
        template: str
        context: dict

    recorded = []

    def record(sender, template, context, **extra):
        recorded.append(TemplateContent(template=template, context=context))

    template_rendered.connect(record, app)
    try:
        # TODO: return a named tuple or similar for
        # better structure of template and context
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


def test_get_jobs(db_session, client, captured_templates):
    with freeze_time(now):
        response = client.get("/")

    assert response.status_code == 200
    assert len(captured_templates) == 1
    template, context = captured_templates[0]
    assert template.name == "jobs/index.html"
    assert context["jobs"] == []
    assert context["page"] == 1
    assert context["available_tags"] == AVAILABLE_TAGS
    assert context["per_page"] == PER_PAGE
    assert context["current_filters"] == {
        "min_salary": Decimal("20000"),
        "include_without_salary": False,
        "tags": [],
        "is_remote": True,
        "posted_on": now - timedelta(days=config.JOB_AGE_LIMIT_DAYS),
        "sort": "posted_on_desc",
        "location": None,
    }
    # remove the get_url method from pagination
    # as it is not needed in the test
    context["pagination"].pop("get_url")
    assert context["pagination"] == {
        "page": 1,
        "per_page": PER_PAGE,
        "total_pages": 0,
        "total_jobs": 0,
        "has_prev": False,
        "has_next": False,
    }


@patch("job_board.views.PER_PAGE", new=1)
@freeze_time(now)
def test_get_jobs_with_filters(db_session, client, captured_templates):
    store_jobs(
        [
            JobListing(
                link="https://example.com/job1",
                title="Job 1",
                min_salary=30000,
                is_remote=True,
                posted_on=now - timedelta(days=10),
                description="A job description",
                tags=["python", "remote"],
                payload="some data",
                company_name="Test Company",
            ),
            JobListing(
                link="https://example.com/job2",
                title="Job 2",
                min_salary=25000,
                is_remote=True,
                posted_on=now - timedelta(days=20),
                description="Another job description",
                tags=["python"],
                payload="some data",
                company_name="Test Company",
            ),
            JobListing(
                link="https://example.com/job3",
                title="Job 3",
                min_salary=None,
                is_remote=True,
                posted_on=now - timedelta(days=5),
                description="A third job description",
                tags=["developer"],
                payload="some data",
                company_name="Test Company",
            ),
        ]
    )

    # all jobs
    response = client.get(
        "/",
        query_string={
            "min_salary": 20000,
            "include_without_salary": True,
        },
    )

    assert response.status_code == 200
    context = captured_templates[-1].context
    assert len(context["jobs"]) == 1
    assert context["pagination"]["total_jobs"] == 3
    assert context["pagination"]["total_pages"] == 3

    # all but one without salary
    response = client.get(
        "/",
        query_string={
            "min_salary": 20000,
            "include_without_salary": False,
            "tags": ["python", "remote"],
            "is_remote": True,
        },
    )

    assert response.status_code == 200
    context = captured_templates[-1].context
    assert len(context["jobs"]) == 1
    pagination = context["pagination"]
    assert pagination["total_jobs"] == 2
    assert pagination["total_pages"] == 2
    assert pagination["has_next"] is True
    assert pagination["has_prev"] is False

    # filters are preserved across pagination
    response = client.get(
        "/",
        query_string={
            "min_salary": 20000,
            "tags": ["python", "remote"],
            "is_remote": True,
            "page": 2,
        },
    )

    assert response.status_code == 200
    context = captured_templates[-1].context
    assert len(context["jobs"]) == 1
    pagination = context["pagination"]
    assert pagination["total_jobs"] == 2
    assert pagination["total_pages"] == 2
    assert pagination["has_next"] is False
    assert pagination["has_prev"] is True
    assert pagination["page"] == 2
    filters = context["current_filters"]
    assert filters["min_salary"] == 20000
    assert filters["include_without_salary"] is False
    assert filters["tags"] == ["python", "remote"]
    assert filters["is_remote"] is True
    assert filters["sort"] == "posted_on_desc"


def test_get_jobs_sorting(db_session, client, captured_templates):
    response = client.get("/", query_string={"sort": "blah"})
    assert response.status_code == 400

    link_1 = "https://example.com/job1"
    link_2 = "https://example.com/job2"
    job_1 = JobListing(
        link=link_1,
        title="Job 1",
        min_salary=30_000,
        is_remote=True,
        tags=["python", "remote"],
        description="A job description",
        payload="some data",
        company_name="Test Company",
    )
    job_2 = JobListing(
        link=link_2,
        title="Job 2",
        min_salary=25_000,
        is_remote=True,
        description="Another job description",
        tags=["python"],
        payload="some data",
        company_name="Test Company",
    )

    store_jobs([job_1, job_2])

    response = client.get(
        "/",
        query_string={
            "sort": "salary_desc",
        },
    )

    assert response.status_code == 200
    context = captured_templates[-1].context
    assert [j.link for j in context["jobs"]] == [link_1, link_2]

    response = client.get(
        "/",
        query_string={
            "sort": "posted_on_desc",
        },
    )
    assert response.status_code == 200
    context = captured_templates[-1].context
    assert [j.link for j in context["jobs"]] == [link_2, link_1]


def test_location_filtering_and_validation(db_session, client, captured_templates):
    response = client.get("/", query_string={"location": "INVALID"})
    assert response.status_code == 400

    us_job = JobListing(
        link="https://example.com/us-job",
        title="US Job",
        locations=["US"],
        min_salary=50_000,
        tags=["python"],
        is_remote=True,
        payload="some data",
        company_name="Test Company",
    )
    india_job = JobListing(
        link="https://example.com/india-job",
        title="India Job",
        locations=["IN"],
        min_salary=50_000,
        tags=["python"],
        is_remote=True,
        payload="some data",
        company_name="Test Company",
    )
    ca_job = JobListing(
        link="https://example.com/ca-job",
        title="California Job",
        locations=["US-CA"],
        min_salary=50_000,
        tags=["python"],
        is_remote=True,
        payload="some data",
        company_name="Test Company",
    )
    no_location_job = JobListing(
        link="https://example.com/no-location-job",
        title="No Location Job",
        locations=None,
        min_salary=50_000,
        tags=["python"],
        is_remote=True,
        payload="some data",
        company_name="Test Company",
    )

    store_jobs(
        [
            us_job,
            india_job,
            ca_job,
            no_location_job,
        ]
    )

    response = client.get("/", query_string={"location": "us"})
    assert response.status_code == 200
    context = captured_templates[-1].context
    links = {job.link for job in context["jobs"]}
    assert links == {us_job.link, ca_job.link, no_location_job.link}

    response = client.get("/")
    assert response.status_code == 200
    context = captured_templates[-1].context
    links = {job.link for job in context["jobs"]}
    assert links == {ca_job.link, us_job.link, india_job.link, no_location_job.link}
