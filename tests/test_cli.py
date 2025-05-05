from datetime import datetime
from datetime import timezone
from unittest import mock

import pytest
from click.testing import CliRunner

from job_board.cli import _fetch
from job_board.cli import debugger_hook
from job_board.cli import main
from job_board.portals import PORTALS
from job_board.portals.models import PortalSetting


@pytest.fixture
def cli_runner():
    return CliRunner()


def test_run_command_default_options(cli_runner):
    with mock.patch("job_board.cli._fetch") as mock_run:
        result = cli_runner.invoke(main, ["fetch"])

    assert result.exit_code == 0
    mock_run.assert_called_once_with(
        include_portals=(), exclude_portals=(), to_notify=False
    )


def test_run_command_with_pdb_flag(cli_runner):
    with (
        mock.patch("job_board.cli._fetch") as mock_run,
        mock.patch("job_board.cli.sys") as mock_sys,
    ):
        result = cli_runner.invoke(main, ["fetch", "--pdb"])

    assert result.exit_code == 0
    assert mock_sys.excepthook == debugger_hook
    mock_run.assert_called_once_with(
        include_portals=(), exclude_portals=(), to_notify=False
    )


def test_run_command_with_notify_flag(cli_runner):
    with mock.patch("job_board.cli._fetch") as mock_run:
        result = cli_runner.invoke(main, ["fetch", "--notify"])

    assert result.exit_code == 0
    mock_run.assert_called_once_with(
        include_portals=(), exclude_portals=(), to_notify=True
    )


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
                "get_jobs",
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


def test_fetch_function_all_portals(db_session, mock_portals):
    mock_portals()
    with (
        mock.patch("job_board.cli.init_db") as mock_init_db,
        mock.patch("job_board.cli.click.echo") as mock_echo,
        mock.patch("job_board.cli.store_jobs") as mock_store_jobs,
        mock.patch("job_board.cli.notify") as mock_notify,
    ):
        _fetch()

    mock_init_db.assert_called_once()
    assert mock_store_jobs.call_count == len(PORTALS)
    mock_notify.assert_not_called()

    assert mock_echo.call_count >= 3


def test_fetch_function_specific_portal(db_session, mock_portals):
    mock_portals(portals=["weworkremotely"])

    with (
        mock.patch("job_board.cli.init_db") as mock_init_db,
        mock.patch("job_board.cli.click.echo"),
        mock.patch("job_board.cli.store_jobs") as mock_store_jobs,
        mock.patch("job_board.cli.notify") as mock_notify,
    ):
        _fetch(include_portals=["weworkremotely"])

    mock_init_db.assert_called_once()
    mock_store_jobs.assert_called_once()
    mock_notify.assert_not_called()


def test_fetch_function_with_notify(db_session, mock_portals):
    mock_portals()

    with (
        mock.patch("job_board.cli.init_db"),
        mock.patch("job_board.cli.click.echo"),
        mock.patch("job_board.cli.store_jobs"),
        mock.patch("job_board.cli.notify") as mock_notify,
    ):
        _fetch(to_notify=True)

    mock_notify.assert_called_once()


def test_schedule_command(cli_runner):
    mock_schedule_run_pending = mock.MagicMock(
        side_effect=[None, SystemExit("exit the loop")]
    )

    with (
        mock.patch("job_board.cli.schedule") as mock_schedule,
        mock.patch("job_board.cli.time.sleep"),
    ):
        mock_schedule.run_pending = mock_schedule_run_pending

        result = cli_runner.invoke(main, ["schedule"])

    assert isinstance(result.exception, SystemExit)
    assert mock_schedule.every().day.at.called
    assert mock_schedule.run_pending.call_count == 2


def test_schedule_command_immediate(cli_runner):
    with mock.patch("job_board.cli.schedule") as mock_schedule:
        result = cli_runner.invoke(main, ["schedule", "--immediate"])

    assert result.exit_code == 0
    mock_schedule.run_all.assert_called_once()


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
    assert "fetch" in result.output
    assert "schedule" in result.output
    assert "setup-db" in result.output
