from unittest import mock

import pytest

from job_board import models
from job_board.cli import fetch_jobs
from job_board.portals import PORTALS
from job_board.scheduler import scheduler


@pytest.fixture
def mock_fetch():
    with mock.patch(
        "job_board.schedules.cli.fetch_jobs", spec_set=fetch_jobs
    ) as mock_fetch:
        yield mock_fetch


def test_scheduled_jobs_creates_job_per_portal():
    jobs = scheduler.list_jobs()

    for portal_name in PORTALS:
        assert f"fetch_{portal_name}_jobs" in jobs


def test_wellfound_job_function(mock_fetch):
    scheduler.run_job("fetch_wellfound_jobs")

    mock_fetch.assert_called_once_with(include_portals=["wellfound"])


def test_non_wellfound_job_function(mock_fetch):
    jobs = scheduler.list_jobs()
    non_wellfound_job = next(job for job in jobs if job != "fetch_wellfound_jobs")

    scheduler.run_job(non_wellfound_job)

    mock_fetch.assert_called_once()
    _, kwargs = mock_fetch.call_args
    (portal_name,) = kwargs["include_portals"]
    assert portal_name in PORTALS


def test_purge_old_jobs():
    with mock.patch.object(models, "purge_old_jobs") as mock_purge:
        scheduler.run_job("purge_old_jobs")

    mock_purge.assert_called_once()
