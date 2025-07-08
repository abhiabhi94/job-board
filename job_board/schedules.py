from job_board import cli
from job_board import models
from job_board.portals import PORTALS
from job_board.scheduler import scheduler


# Schedule individual portal jobs to isolate failures
for portal_name in PORTALS:

    def create_portal_job(name):
        def fetch_jobs_func():
            cli.fetch_jobs(include_portals=[name])

        # Set unique name before decorating, since the scheduler
        # uses the function name as the job ID, which must be unique.
        fetch_jobs_func.__name__ = f"fetch_{name}_jobs"
        # run at 1 AM/PM daily, running at 12 results in an error
        # since the exchange rate is not available at midnight.
        return scheduler.schedule("0 1,13 * * *")(fetch_jobs_func)

    create_portal_job(portal_name)


@scheduler.schedule("0 0 * * *")
def purge_old_jobs():
    models.purge_old_jobs()
