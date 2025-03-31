import subprocess
import pdb
import sys
import traceback
import time

import click
import schedule

from job_board.portals import PORTALS
from job_board.models import store_jobs
from job_board.models import create_tables, notify
from job_board.logger import logger


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


@main.command("run", help="Run the notifier")
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
def run(pdb_flag, include_portals, exclude_portals, to_notify):
    if pdb_flag:
        sys.excepthook = debugger_hook

    if include_portals and exclude_portals:
        raise click.UsageError(
            "Cannot use --include-portals and --exclude-portals at the same time."
        )

    _run(
        include_portals=include_portals,
        exclude_portals=exclude_portals,
        to_notify=to_notify,
    )


def _run(
    *,
    include_portals: list[str] | None = None,
    exclude_portals: list[str] | None = None,
    to_notify=False,
):
    create_tables()
    click.echo("********Notifier started**********")

    if not include_portals and not exclude_portals:
        click.echo("Fetching jobs from all portals")
        portals = list(PORTALS.keys())

    # TODO: validate that the portal exists
    elif include_portals:
        portals = include_portals
    else:
        portals = list(set(PORTALS.keys()) - set(exclude_portals))

    portals = list(map(str.lower, portals))

    jobs = []
    for portal_name, portal_class in PORTALS.items():
        if portal_name.lower() in portals:
            click.echo(f"Fetching jobs from {portal_name.title()}")
            fetched_jobs = portal_class().get_jobs()
            logger.debug(f"Jobs from {portal_name}:\n\n{fetched_jobs}")
            jobs.extend(fetched_jobs)

    store_jobs(jobs)

    if to_notify:
        notify()
    else:
        click.echo(f"Jobs to notify:\n {'\n'.join(map(str, jobs))}\n")
        click.echo("Notifications are disabled")

    click.echo("********Notifier completed**********")


@main.command("schedule", help="Schedule the notifier")
@click.option("--immediate", "-I", is_flag=True, help="Run the scheduler immediately")
def schedule_notifier(immediate):
    schedule.every().day.at("10:30").do(_run, to_notify=True)
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
