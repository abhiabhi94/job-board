import pdb
import subprocess
import sys
import time
import traceback
from datetime import timedelta
from datetime import timezone

import click

# Import scheduled jobs to register them globally  # noreorder
import job_board.schedules  # noqa: F401
from job_board import config
from job_board.connection import get_session
from job_board.init_db import init_db
from job_board.logger import logger
from job_board.models import store_jobs
from job_board.portals import PORTALS
from job_board.portals.models import PortalSetting
from job_board.scheduler import scheduler
from job_board.utils import log_to_sentry
from job_board.utils import utcnow_naive


def debugger_hook(exception_type, value, tb):
    """
    Hook to drop into pdb on an unhandled exception.
    Used with --pdb flag, helpful for debugging purposes.
    """
    traceback.print_exception(exception_type, value, tb)

    click.echo("\n Exception occurred! Launching pdb debugger...\n", file=sys.stderr)
    pdb.post_mortem(tb)


@click.group()
def main():
    pass


@main.command("fetch", help="Fetch jobs from portals")
@click.option(
    "--pdb", "pdb_flag", is_flag=True, default=False, help="Drop into pdb on exception."
)
@click.option(
    "--include-portals",
    "-I",
    "include_portals",
    type=str,
    multiple=True,
    help=(
        "Portals to include for fetching jobs, cannot be used with --ignore-portal. "
        "By default, all portals are included."
    ),
)
@click.option(
    "--exclude-portals",
    "-E",
    "exclude_portals",
    type=str,
    multiple=True,
    help="Portals to ignore when fetching jobs, cannot be used with --include-portals",
)
def fetch(pdb_flag, include_portals, exclude_portals):
    if pdb_flag or config.ENV == "dev":
        sys.excepthook = debugger_hook

    if include_portals and exclude_portals:
        raise click.UsageError(
            "Cannot use --include-portals and --exclude-portals at the same time."
        )

    fetch_jobs(
        include_portals=include_portals,
        exclude_portals=exclude_portals,
    )


def fetch_jobs(
    *,
    include_portals: list[str] | None = None,
    exclude_portals: list[str] | None = None,
):
    init_db()
    click.echo("********Fetching Jobs**********")

    if not include_portals and not exclude_portals:
        click.echo("Fetching jobs from all portals")
        portals = list(PORTALS.keys())

    elif include_portals:
        portals = include_portals
    else:
        portals = list(set(PORTALS.keys()) - set(exclude_portals))

    portals = list(map(str.lower, portals))

    for portal_name, portal_class in PORTALS.items():
        if portal_name.lower() in portals:
            click.echo(f"Fetching jobs from {portal_name.title()}")
            setting = PortalSetting.get_or_create(portal_name=portal_name)
            setting_id = setting.id
            last_run_at = None
            if setting.last_run_at:
                last_run_at = setting.last_run_at.astimezone(timezone.utc)
                # just to have a buffer.
                last_run_at -= timedelta(minutes=5)

            portal = portal_class(last_run_at=last_run_at)
            jobs = portal.fetch_jobs()
            logger.debug(f"Jobs from {portal_name}:\n\n{jobs}")
            store_jobs(jobs)

            with get_session(readonly=False) as session:
                setting = session.get(PortalSetting, setting_id)
                setting.last_run_at = utcnow_naive()

    click.echo("********Fetched jobs**********")


@main.group("scheduler", help="Job scheduler commands")
def scheduler_group():
    pass


@scheduler_group.command("start", help="Start the job scheduler")
def start_scheduler():
    try:
        _start_scheduler()
    except Exception as e:
        log_to_sentry(e, "scheduler")
        raise


def _start_scheduler():
    scheduler.start()
    click.echo("Scheduler started.\nPress Ctrl+C to stop...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("Stopping scheduler...")
        scheduler.stop()
        click.echo("Scheduler stopped.")


@scheduler_group.command("remove-jobs", help="Remove all scheduled jobs")
def remove_jobs():
    scheduler.clear_jobs()


@scheduler_group.command("stop", help="Stop the job scheduler")
def stop_scheduler():
    scheduler.clear_jobs()
    scheduler.stop()


@scheduler_group.command("list-jobs", help="List all registered jobs")
def list_jobs():
    jobs = scheduler.list_jobs()
    if jobs:
        click.echo("Registered jobs:")
        for job_name in jobs:
            click.echo(f"  - {job_name}")
    else:
        click.echo("No jobs registered")


@scheduler_group.command("run-job", help="Run a specific job")
@click.argument("job-name")
def run_job(job_name):
    scheduler.run_job(job_name)
    click.echo(f"Job '{job_name}' executed successfully")


@main.command("setup-db", help="Setup the PostgreSQL database")
@click.option("--db-name", "-d", default="job_board", help="Name of the database")
@click.option("--username", "-u", default="job_board", help="Username for the database")
@click.option("--password", "-p", default="job_board", help="Password for the user")
def setup_db(username: str, password: str, db_name: str):
    """
    Creates a PostgreSQL user with LOGIN and CREATEDB permissions
    and assigns ownership of the database.

    :param username: Name of the PostgreSQL user to create.
    :param password: Password for the new PostgreSQL user.
    :param db_name: Name of the database to create.
    """
    subprocess.run(
        [
            "psql",
            "-c",
            f"CREATE ROLE {username} WITH LOGIN PASSWORD '{password}' CREATEDB;",
        ],
        check=True,
    )
    subprocess.run(
        [
            "psql",
            "-c",
            f"CREATE DATABASE {db_name} WITH OWNER {username};",
        ],
        check=True,
    )
    click.echo("Database setup completed successfully.")


@main.command("runserver", help="Run the Flask development server")
@click.option("--host", "-h", default="127.0.0.1", help="The host to bind to")
@click.option("--port", "-p", default=5000, help="The port to bind to")
@click.option("--debug", "-d", is_flag=True, default=False, help="Enable debug mode")
def runserver(host: str, port: int, debug: bool):
    """
    Runs the Flask development server with the specified host, port, and debug settings.

    :param host: The host to bind the server to
    :param port: The port to bind the server to
    :param debug: Whether to run the server in debug mode
    """
    from job_board.views import app

    click.echo(f"Starting server on {host}:{port}")
    if config.ENV == "dev":
        sys.excepthook = debugger_hook
    app.run(host=host, port=port, debug=debug)
