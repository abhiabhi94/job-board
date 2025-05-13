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
        "include_no_salary": False,
        "tags": [],
        "is_remote": True,
        "posted_on": now - timedelta(days=config.JOB_AGE_LIMIT_DAYS),
        "sort": "posted_on_desc",
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
                salary=30000,
                is_remote=True,
                posted_on=now - timedelta(days=10),
                description="A job description",
                tags=["python", "remote"],
                payload="some data",
            ),
            JobListing(
                link="https://example.com/job2",
                title="Job 2",
                salary=25000,
                is_remote=True,
                posted_on=now - timedelta(days=20),
                description="Another job description",
                tags=["python"],
                payload="some data",
            ),
            JobListing(
                link="https://example.com/job3",
                title="Job 3",
                salary=None,
                is_remote=True,
                posted_on=now - timedelta(days=5),
                description="A third job description",
                tags=["developer"],
                payload="some data",
            ),
        ]
    )

    # all jobs
    response = client.get(
        "/",
        query_string={
            "min_salary": 20000,
            "include_no_salary": True,
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
            "include_no_salary": False,
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
    assert filters["include_no_salary"] is False
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
        salary=30000,
        is_remote=True,
        tags=["python", "remote"],
        description="A job description",
        payload="some data",
    )
    job_2 = JobListing(
        link=link_2,
        title="Job 2",
        salary=25000,
        is_remote=True,
        description="Another job description",
        tags=["python"],
        payload="some data",
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
