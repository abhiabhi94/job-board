from job_board import cli
from job_board import models
from job_board.models import Job
from job_board.portals import PORTALS
from job_board.portals import Wellfound
from job_board.scheduler import scheduler


# Schedule individual portal jobs to isolate failures
for portal_name in PORTALS:
    if portal_name == Wellfound.portal_name:
        # wellfound is scheduled separately so that
        # since it consumes a lot of scrapfly credits.
        # This is to avoid running it multiple times a day.
        continue

    def create_portal_job(name):
        def fetch_jobs_func():
            cli.fetch_jobs(include_portals=[name])

        # Set unique name before decorating, since the scheduler
        # uses the function name as the job ID, which must be unique.
        fetch_jobs_func.__name__ = f"fetch_{name}_jobs"
        # run at 1 AM/PM daily, running at 12 results in an error
        # since the exchange rate is not available at midnight.
        return scheduler.schedule(minute=0, hour="1,13")(fetch_jobs_func)

    create_portal_job(portal_name)


@scheduler.schedule(minute=0, hour=12)
def fetch_wellfound_jobs():
    cli.fetch_jobs(include_portals=[Wellfound.portal_name])


@scheduler.schedule(minute=0, hour=0)
def purge_old_jobs():
    models.purge_old_jobs()


@scheduler.schedule(minute="*/5")
def fill_missing_tags():
    Job.fill_missing_tags()
