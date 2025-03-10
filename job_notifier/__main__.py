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
def run():
    _run()


def _run():
    create_tables()
    click.echo("********Notifier started**********")
    messages = weworkremotely.WeWorkRemotely().get_messages_to_notify()
    store_jobs(messages)
    notify()
    click.echo("********Notifier completed**********")


@cli.command("schedule", help="Schedule the notifier")
@click.option("--immediate", "-I", is_flag=True, help="Run the scheduler immediately")
def schedule_notifier(immediate):
    schedule.every().day.at("10:30").do(_run)
    if immediate:
        schedule.run_all(5)
        click.echo("All schedules executed")
        return

    while True:
        schedule.run_pending()
        time.sleep(1)


cli.add_command(run)
cli.add_command(schedule_notifier)

if __name__ == "__main__":
    cli()
