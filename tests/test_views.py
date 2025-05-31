from datetime import timedelta
from decimal import Decimal

import pytest
from flask import template_rendered
from freezegun import freeze_time

from job_board import config
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
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

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
