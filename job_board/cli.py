import pdb
import subprocess
import sys
import time
import traceback
from datetime import timedelta
from datetime import timezone

import click
import schedule

from job_board.connection import get_session
from job_board.init_db import init_db
from job_board.logger import logger
from job_board.models import notify
from job_board.models import store_jobs
from job_board.portals import PORTALS
from job_board.portals.models import PortalSetting
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
    "--notify",
    "-n",
    "to_notify",
    is_flag=True,
    default=False,
    help="Send notifications, by default it will only print the job_listing",
)
@click.option(
    "--include-portals",
    "-P",
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
def fetch(pdb_flag, include_portals, exclude_portals, to_notify):
    if pdb_flag:
        sys.excepthook = debugger_hook

    if include_portals and exclude_portals:
        raise click.UsageError(
            "Cannot use --include-portals and --exclude-portals at the same time."
        )

    _fetch(
        include_portals=include_portals,
        exclude_portals=exclude_portals,
        to_notify=to_notify,
    )


def _fetch(
    *,
    include_portals: list[str] | None = None,
    exclude_portals: list[str] | None = None,
    to_notify=False,
):
    init_db()
    click.echo("********Fetching Jobs**********")

    if not include_portals and not exclude_portals:
        click.echo("Fetching jobs from all portals")
        portals = list(PORTALS.keys())

    # TODO: validate that the portal exists
    elif include_portals:
        portals = include_portals
    else:
        portals = list(set(PORTALS.keys()) - set(exclude_portals))

    portals = list(map(str.lower, portals))

    all_jobs = []
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

            jobs = portal_class(last_run_at=last_run_at).get_jobs()
            logger.debug(f"Jobs from {portal_name}:\n\n{jobs}")
            store_jobs(jobs)
            all_jobs.extend(jobs)

            with get_session(readonly=False) as session:
                setting = session.get(PortalSetting, setting_id)
                setting.last_run_at = utcnow_naive()

    if to_notify:
        notify()
    else:
        click.echo(f"Jobs to notify:\n {'\n'.join(map(str, all_jobs))}\n")
        click.echo("Notifications are disabled")

    click.echo("********Fetched jobs**********")


@main.command("schedule", help="Schedule the notifier")
@click.option("--immediate", "-I", is_flag=True, help="Run the scheduler immediately")
def schedule_notifier(immediate):
    click.echo("********Scheduling Notifier**********")
    schedule.every().day.at("10:30").do(_fetch, to_notify=True)
    if immediate:
        schedule.run_all(delay_seconds=5)
        click.echo("All schedules executed")
        return

    while True:
        schedule.run_pending()
        time.sleep(1)


@main.command("setup-db", help="Schedule the notifier")
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
