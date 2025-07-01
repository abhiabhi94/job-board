from datetime import datetime
from datetime import timezone
from unittest import mock

import pytest
from click.testing import CliRunner

from job_board import config
from job_board.cli import debugger_hook
from job_board.cli import fetch_jobs
from job_board.cli import main
from job_board.portals import PORTALS
from job_board.portals.models import PortalSetting


@pytest.fixture
def cli_runner():
    return CliRunner()


def test_run_command_default_options(cli_runner):
    with mock.patch("job_board.cli.fetch_jobs") as mock_run:
        result = cli_runner.invoke(main, ["fetch"])

    assert result.exit_code == 0
    mock_run.assert_called_once_with(include_portals=(), exclude_portals=())


def test_run_command_exception_hook(cli_runner):
    with (
        mock.patch("job_board.cli.fetch_jobs") as mock_run,
        mock.patch("job_board.cli.sys") as mock_sys,
    ):
        result = cli_runner.invoke(main, ["fetch", "--pdb"])

    assert result.exit_code == 0
    assert mock_sys.excepthook == debugger_hook
    mock_run.assert_called_once_with(include_portals=(), exclude_portals=())

    with (
        mock.patch.object(config, "ENV", "dev"),
        mock.patch("job_board.cli.fetch_jobs"),
        mock.patch("job_board.cli.sys") as mock_sys,
    ):
        result = cli_runner.invoke(main, ["fetch"])

    assert result.exit_code == 0
    assert mock_sys.excepthook == debugger_hook


@pytest.fixture
def mock_portals(monkeypatch):
    mock_methods = []

    def _mock_portals(portals=None):
        if portals is None:
            portals = PORTALS.keys()

        for portal_name, portal_class in PORTALS.items():
            if portal_name not in portals:
                continue

            mock_method = mock.MagicMock(return_value=[f"job-{portal_name}"])
            monkeypatch.setattr(
                portal_class,
                "fetch_jobs",
                value=mock_method,
            )
            mock_methods.append(mock_method)

        return mock_methods

    yield _mock_portals

    for mock_method in mock_methods:
        mock_method.assert_called_once()


def test_run_command_with_include_portal_option(cli_runner, mock_portals, db_session):
    portal_name = "weworkremotely"
    setting = PortalSetting.get_or_create(portal_name=portal_name)
    assert setting.last_run_at is None

    mock_portals(portals=[portal_name])
    with mock.patch("job_board.cli.store_jobs") as mock_store_jobs:
        result = cli_runner.invoke(main, ["fetch", "--include-portals", portal_name])

    assert result.exit_code == 0
    mock_store_jobs.assert_called_once()

    db_session.flush()
    assert db_session.get(PortalSetting, setting.id).last_run_at is not None


def test_run_command_with_last_run_at(cli_runner, mock_portals, db_session):
    now = datetime.now(timezone.utc)
    setting = PortalSetting.get_or_create(portal_name="weworkremotely")
    setting.last_run_at = now
    db_session.add(setting)

    mock_portals(portals=["weworkremotely"])
    with mock.patch("job_board.cli.store_jobs") as mock_store_jobs:
        result = cli_runner.invoke(
            main, ["fetch", "--include-portals", "weworkremotely"]
        )
    assert result.exit_code == 0
    mock_store_jobs.assert_called_once()


def test_run_command_with_exclude_portals_option(cli_runner, db_session, mock_portals):
    portals = list(set(PORTALS.keys()) - set(["weworkremotely", "remotive"]))
    mock_portals(portals=portals)
    with mock.patch("job_board.cli.store_jobs") as mock_store_jobs:
        result = cli_runner.invoke(
            main,
            [
                "fetch",
                "--exclude-portals",
                "weworkremotely",
                "--exclude-portals",
                "remotive",
            ],
        )

    assert result.exit_code == 0
    assert mock_store_jobs.call_count == len(portals)


def test_run_command_with_both_include_and_exclude_portal_option(cli_runner):
    result = cli_runner.invoke(
        main,
        [
            "fetch",
            "--include-portals",
            "weworkremotely",
            "--exclude-portals",
            "remotive",
        ],
    )

    assert isinstance(result.exception, SystemExit)


def test_fetch_jobs_function_all_portals(db_session, mock_portals):
    mock_portals()
    with (
        mock.patch("job_board.cli.init_db") as mock_init_db,
        mock.patch("job_board.cli.click.echo") as mock_echo,
        mock.patch("job_board.cli.store_jobs") as mock_store_jobs,
    ):
        fetch_jobs()

    mock_init_db.assert_called_once()
    assert mock_store_jobs.call_count == len(PORTALS)

    assert mock_echo.call_count >= 3


def test_fetch_jobs_function_specific_portal(db_session, mock_portals):
    mock_portals(portals=["weworkremotely"])

    with (
        mock.patch("job_board.cli.init_db") as mock_init_db,
        mock.patch("job_board.cli.click.echo"),
        mock.patch("job_board.cli.store_jobs") as mock_store_jobs,
    ):
        fetch_jobs(include_portals=["weworkremotely"])

    mock_init_db.assert_called_once()
    mock_store_jobs.assert_called_once()


def test_scheduler_command(cli_runner):
    with (
        mock.patch("job_board.cli.scheduler") as mock_scheduler,
    ):
        result = cli_runner.invoke(main, ["scheduler", "list-jobs"])

        assert result.exit_code == 0
        mock_scheduler.list_jobs.assert_called_once()

        result = cli_runner.invoke(main, ["scheduler", "run-job", "test_job"])
        assert result.exit_code == 0
        mock_scheduler.run_job.assert_called_once_with("test_job")

        result = cli_runner.invoke(main, ["scheduler", "remove-jobs"])
        assert result.exit_code == 0
        mock_scheduler.clear_jobs.assert_called_once()

        result = cli_runner.invoke(main, ["scheduler", "stop"])
        assert result.exit_code == 0
        # 1 call from remove-jobs above, 1 from stop
        assert mock_scheduler.clear_jobs.call_count == 2
        mock_scheduler.stop.assert_called_once()


def test_scheduler_start_command(cli_runner):
    with (
        mock.patch("job_board.cli.scheduler") as mock_scheduler,
        mock.patch(
            "job_board.cli.time.sleep", side_effect=[None, None, KeyboardInterrupt()]
        ) as mock_sleep,
    ):
        result = cli_runner.invoke(main, ["scheduler", "start"])

    assert result.exit_code == 0
    mock_scheduler.start.assert_called_once()
    assert mock_sleep.call_count == 3
    mock_scheduler.stop.assert_called_once()


def test_setup_db_command(cli_runner):
    with mock.patch("job_board.cli.subprocess.run") as mock_run:
        result = cli_runner.invoke(main, ["setup-db"])

    assert result.exit_code == 0
    assert mock_run.call_count == 2


def test_setup_db_command_with_options(cli_runner):
    with mock.patch("job_board.cli.subprocess.run") as mock_run:
        result = cli_runner.invoke(
            main,
            [
                "setup-db",
                "--db-name",
                "testdb",
                "--username",
                "testuser",
                "--password",
                "testpass",
            ],
        )

    assert result.exit_code == 0
    assert mock_run.call_count == 2

    # Verify correct parameters were passed
    create_user_call_args = mock_run.call_args_list[0][0][0]
    # The SQL command string is the third element in the subprocess.run args
    create_user_sql = create_user_call_args[2]
    assert "testuser" in create_user_sql
    assert "testpass" in create_user_sql

    create_db_call_args = mock_run.call_args_list[1][0][0]
    # The SQL command string is the third element in the subprocess.run args
    create_db_sql = create_db_call_args[2]
    assert "testdb" in create_db_sql
    assert "testuser" in create_db_sql


def test_debugger_hook():
    mock_exception = ValueError("Test exception")
    mock_tb = mock.MagicMock()

    with (
        mock.patch("job_board.cli.traceback.print_exception") as mock_print_exception,
        mock.patch("job_board.cli.click.echo") as mock_echo,
        mock.patch("job_board.cli.pdb.post_mortem") as mock_post_mortem,
    ):
        debugger_hook(ValueError, mock_exception, mock_tb)

    mock_print_exception.assert_called_once_with(ValueError, mock_exception, mock_tb)
    mock_echo.assert_called_once()
    mock_post_mortem.assert_called_once_with(mock_tb)


def test_cli_group():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    for command in (
        "fetch",
        "schedule",
        "setup-db",
        "runserver",
    ):
        assert command in result.output


def test_runserver_command(cli_runner):
    with (
        mock.patch("job_board.cli.click.echo") as mock_echo,
        mock.patch("job_board.views.app.run") as mock_run,
    ):
        result = cli_runner.invoke(
            main, ["runserver", "--host", "0.0.0.0", "--port", "8080", "--debug"]
        )

    mock_echo.assert_called_once_with("Starting server on 0.0.0.0:8080")
    mock_run.assert_called_once_with(host="0.0.0.0", port=8080, debug=True)
    assert result.exit_code == 0


def test_runserver_command_dev_mode(cli_runner):
    with (
        mock.patch("job_board.config.ENV", "dev"),
        mock.patch("job_board.cli.click.echo") as mock_echo,
        mock.patch("job_board.views.app.run") as mock_run,
        mock.patch("job_board.cli.sys") as mock_sys,
    ):
        result = cli_runner.invoke(main, ["runserver"])
    mock_echo.assert_called_once_with("Starting server on 127.0.0.1:5000")
    mock_run.assert_called_once_with(host="127.0.0.1", port=5000, debug=False)
    # Verify that sys.excepthook was set to debugger_hook due to dev mode.
    assert mock_sys.excepthook == debugger_hook
    assert result.exit_code == 0
