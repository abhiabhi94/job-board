from unittest import mock
import pytest
from click.testing import CliRunner

from job_notifier.cli import main, _run, debugger_hook


@pytest.fixture
def cli_runner():
    return CliRunner()


def test_run_command_default_options(cli_runner):
    with mock.patch("job_notifier.cli._run") as mock_run:
        result = cli_runner.invoke(main, ["run"])

    assert result.exit_code == 0
    mock_run.assert_called_once_with(include_portals=[], to_notify=False)


def test_run_command_with_pdb_flag(cli_runner):
    with (
        mock.patch("job_notifier.cli._run") as mock_run,
        mock.patch("job_notifier.cli.sys") as mock_sys,
    ):
        result = cli_runner.invoke(main, ["run", "--pdb"])

    assert result.exit_code == 0
    assert mock_sys.excepthook == debugger_hook
    mock_run.assert_called_once_with(include_portals=[], to_notify=False)


def test_run_command_with_notify_flag(cli_runner):
    with mock.patch("job_notifier.cli._run") as mock_run:
        result = cli_runner.invoke(main, ["run", "--notify"])

    assert result.exit_code == 0
    mock_run.assert_called_once_with(include_portals=[], to_notify=True)


def test_run_command_with_portal_option(cli_runner):
    with mock.patch("job_notifier.cli._run") as mock_run:
        result = cli_runner.invoke(main, ["run", "--portal", "weworkremotely"])

    assert result.exit_code == 0
    mock_run.assert_called_once_with(
        include_portals=["weworkremotely"], to_notify=False
    )


def test_run_function_all_portals():
    mock_wwr_instance = mock.MagicMock(
        portal_name="weworkremotely",
        get_messages_to_notify=mock.MagicMock(return_value=["job1", "job2"]),
    )

    mock_remotive_instance = mock.MagicMock(
        portal_name="remotive",
        get_messages_to_notify=mock.MagicMock(return_value=["job3"]),
    )

    with (
        mock.patch("job_notifier.cli.create_tables") as mock_create_tables,
        mock.patch("job_notifier.cli.click.echo") as mock_echo,
        mock.patch(
            "job_notifier.cli.weworkremotely.WeWorkRemotely",
            return_value=mock_wwr_instance,
        ),
        mock.patch(
            "job_notifier.cli.remotive.Remotive", return_value=mock_remotive_instance
        ),
        mock.patch("job_notifier.cli.store_jobs") as mock_store_jobs,
        mock.patch("job_notifier.cli.notify") as mock_notify,
    ):
        _run()

    mock_create_tables.assert_called_once()
    mock_wwr_instance.get_messages_to_notify.assert_called_once()
    mock_remotive_instance.get_messages_to_notify.assert_called_once()
    mock_store_jobs.assert_called_once_with(["job1", "job2", "job3"])
    mock_notify.assert_not_called()
    assert mock_echo.call_count >= 3


def test_run_function_specific_portal():
    mock_wwr_instance = mock.MagicMock(portal_name="weworkremotely")
    mock_wwr_instance.get_messages_to_notify.return_value = ["job1", "job2"]

    mock_remotive_instance = mock.MagicMock()
    mock_remotive_instance.name = "remotive"
    mock_remotive_instance.get_messages_to_notify.return_value = ["job3"]

    with (
        mock.patch("job_notifier.cli.create_tables") as mock_create_tables,
        mock.patch("job_notifier.cli.click.echo"),
        mock.patch(
            "job_notifier.cli.weworkremotely.WeWorkRemotely",
            return_value=mock_wwr_instance,
        ),
        mock.patch(
            "job_notifier.cli.remotive.Remotive", return_value=mock_remotive_instance
        ),
        mock.patch("job_notifier.cli.store_jobs") as mock_store_jobs,
        mock.patch("job_notifier.cli.notify") as mock_notify,
    ):
        _run(include_portals=["weworkremotely"])

    mock_create_tables.assert_called_once()
    mock_wwr_instance.get_messages_to_notify.assert_called_once()
    mock_remotive_instance.get_messages_to_notify.assert_not_called()
    mock_store_jobs.assert_called_once_with(["job1", "job2"])
    mock_notify.assert_not_called()


def test_run_function_with_notify():
    mock_wwr_instance = mock.MagicMock(
        portal_name="weworkremotely",
        get_messages_to_notify=mock.MagicMock(return_value=[]),
    )

    mock_remotive_instance = mock.MagicMock(
        portal_name="remotive", get_messages_to_notify=mock.MagicMock(return_value=[])
    )

    with (
        mock.patch("job_notifier.cli.create_tables"),
        mock.patch("job_notifier.cli.click.echo"),
        mock.patch(
            "job_notifier.cli.weworkremotely.WeWorkRemotely",
            return_value=mock_wwr_instance,
        ),
        mock.patch(
            "job_notifier.cli.remotive.Remotive", return_value=mock_remotive_instance
        ),
        mock.patch("job_notifier.cli.store_jobs"),
        mock.patch("job_notifier.cli.notify") as mock_notify,
    ):
        _run(to_notify=True)

    mock_notify.assert_called_once()


def test_schedule_command(cli_runner):
    mock_schedule_run_pending = mock.MagicMock(
        side_effect=[None, SystemExit("exit the loop")]
    )

    with (
        mock.patch("job_notifier.cli.schedule") as mock_schedule,
        mock.patch("job_notifier.cli.time.sleep"),
    ):
        mock_schedule.run_pending = mock_schedule_run_pending

        result = cli_runner.invoke(main, ["schedule"])

    assert isinstance(result.exception, SystemExit)
    assert mock_schedule.every().day.at.called
    assert mock_schedule.run_pending.call_count == 2


def test_schedule_command_immediate(cli_runner):
    with mock.patch("job_notifier.cli.schedule") as mock_schedule:
        result = cli_runner.invoke(main, ["schedule", "--immediate"])

    assert result.exit_code == 0
    mock_schedule.run_all.assert_called_once()


def test_setup_db_command(cli_runner):
    with mock.patch("job_notifier.cli.subprocess.run") as mock_run:
        result = cli_runner.invoke(main, ["setup-db"])

    assert result.exit_code == 0
    assert mock_run.call_count == 2


def test_setup_db_command_with_options(cli_runner):
    with mock.patch("job_notifier.cli.subprocess.run") as mock_run:
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
        mock.patch(
            "job_notifier.cli.traceback.print_exception"
        ) as mock_print_exception,
        mock.patch("job_notifier.cli.click.echo") as mock_echo,
        mock.patch("job_notifier.cli.pdb.post_mortem") as mock_post_mortem,
    ):
        debugger_hook(ValueError, mock_exception, mock_tb)

    mock_print_exception.assert_called_once_with(ValueError, mock_exception, mock_tb)
    mock_echo.assert_called_once()
    mock_post_mortem.assert_called_once_with(mock_tb)


def test_cli_group():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.output
    assert "schedule" in result.output
    assert "setup-db" in result.output
