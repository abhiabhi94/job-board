import subprocess

import click

from job_notifier.portals import (
    weworkremotely,
)
from job_notifier.models import store_jobs
import schedule
import time
from job_notifier.models import create_tables, notify


@click.group()
def cli():
    pass


@cli.command("run", help="Run the notifier")
@click.option(
    "--notify",
    "-n",
    is_flag=True,
    default=False,
    help="Do not send notifications",
)
def run(notify):
    _run(to_notify=notify)


def _run(*, to_notify=False):
    create_tables()
    click.echo("********Notifier started**********")
    messages = weworkremotely.WeWorkRemotely().get_messages_to_notify()
    store_jobs(messages)

    if to_notify:
        notify()
    else:
        click.echo(f"Messages to notify:\n {'\n'.join(map(str, messages))}\n")
        click.echo("Notifications are disabled")

    click.echo("********Notifier completed**********")


@cli.command("schedule", help="Schedule the notifier")
@click.option("--immediate", "-I", is_flag=True, help="Run the scheduler immediately")
def schedule_notifier(immediate):
    schedule.every().day.at("10:30").do(_run, to_notify=True)
    if immediate:
        schedule.run_all(5)
        click.echo("All schedules executed")
        return

    while True:
        schedule.run_pending()
        time.sleep(1)


@cli.command("setup-db", help="Schedule the notifier")
@click.option("--db-name", "-d", default="job_notifier", help="Name of the database")
@click.option(
    "--username", "-u", default="job_notifier", help="Username for the database"
)
@click.option("--password", "-p", default="job_notifier", help="Password for the user")
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


if __name__ == "__main__":
    cli()
