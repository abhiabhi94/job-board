from unittest import mock

import pytest

from job_board.scheduler import JobScheduler


def test_scheduler_init():
    test_scheduler = JobScheduler()
    assert test_scheduler._job_registry == {}
    assert test_scheduler._started is False
    assert test_scheduler._scheduler is not None


def test_schedule_decorator():
    test_scheduler = JobScheduler()

    @test_scheduler.schedule("0 10 * * *")
    def test_job():
        pass  # pragma: no cover

    assert "test_job" in test_scheduler._job_registry
    assert test_scheduler._job_registry["test_job"] == test_job

    (job,) = test_scheduler._scheduler.get_jobs()
    assert job.id == "test_job"


def test_schedule_with_invalid_cron_syntax():
    test_scheduler = JobScheduler()

    with pytest.raises(ValueError):

        @test_scheduler.schedule("invalid cron")
        def test_job():
            pass  # pragma: no cover


def test_run_job_success():
    test_scheduler = JobScheduler()
    mocker = mock.MagicMock()

    @test_scheduler.schedule("0 10 * * *")
    def test_job():
        return mocker()

    test_scheduler.run_job("test_job")

    mocker.assert_called_once()


def test_run_job_not_found():
    test_scheduler = JobScheduler()

    with pytest.raises(ValueError, match="Job 'nonexistent' not found"):
        test_scheduler.run_job("nonexistent")


def test_list_jobs():
    test_scheduler = JobScheduler()

    assert test_scheduler.list_jobs() == []

    @test_scheduler.schedule("0 10 * * *")
    def job1():
        pass  # pragma: no cover

    @test_scheduler.schedule("0 11 * * *")
    def job2():
        pass  # pragma: no cover

    jobs = test_scheduler.list_jobs()
    assert set(jobs) == {"job1", "job2"}


def test_start_scheduler():
    """Test starting the scheduler."""
    test_scheduler = JobScheduler()

    with mock.patch.object(test_scheduler._scheduler, "start") as mock_start:
        test_scheduler.start()

        mock_start.assert_called_once()
        assert test_scheduler._started is True

        test_scheduler.start()
        mock_start.assert_called_once()


def test_stop_scheduler():
    test_scheduler = JobScheduler()
    test_scheduler._started = True

    with mock.patch.object(test_scheduler._scheduler, "shutdown") as mock_shutdown:
        test_scheduler.stop()

        mock_shutdown.assert_called_once()
        assert test_scheduler._started is False

        test_scheduler.stop()
        mock_shutdown.assert_called_once()


def test_clear_jobs():
    test_scheduler = JobScheduler()

    @test_scheduler.schedule("0 10 * * *")
    def test_job():
        pass  # pragma: no cover

    with mock.patch.object(test_scheduler._scheduler, "remove_all_jobs") as mock_remove:
        test_scheduler.clear_jobs()

    mock_remove.assert_called_once()


def test_job_scheduler_registering_same_job():
    test_scheduler = JobScheduler()

    @test_scheduler.schedule("0 10 * * *")
    def test_job():
        pass  # pragma: no cover

    with pytest.raises(ValueError, match="Job 'test_job' is already scheduled"):

        @test_scheduler.schedule("0 11 * * *")
        def test_job():
            pass  # pragma: no cover
