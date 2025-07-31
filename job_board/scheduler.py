from typing import Callable
from typing import Dict
from typing import List

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from job_board.logger import logger


class JobScheduler:
    """Simple job scheduler using APScheduler with cron expressions."""

    def __init__(self):
        self._scheduler = BackgroundScheduler()
        self._job_registry: Dict[str, Callable] = {}
        self._started = False

    def schedule(self, **kwargs) -> Callable:
        """
        Decorator to schedule a function with cron expression.

        Examples:
            @scheduler.schedule(minute='*/5')  # Every 5 minutes
            @scheduler.schedule(hour='*/2')  # Every 2 hours
            @scheduler.schedule(day_of_week='mon', hour=9)  # Weekly on Monday at 9 AM
        """

        def decorator(func: Callable):
            job_name = func.__name__
            if job_name in self._job_registry:
                raise ValueError(f"Job '{job_name}' is already scheduled")

            self._job_registry[job_name] = func

            trigger = CronTrigger(**kwargs)
            self._scheduler.add_job(
                func,
                trigger=trigger,
                id=job_name,
            )

            logger.info(f"Scheduled job '{job_name}' with cron '{kwargs}'")
            return func

        return decorator

    def run_job(self, job_name: str):
        if job_name in self._job_registry:
            logger.info(f"Running job: {job_name}")
            self._job_registry[job_name]()
        else:
            raise ValueError(f"Job '{job_name}' not found")

    def list_jobs(self) -> List[str]:
        return list(self._job_registry.keys())

    def start(self):
        if not self._started:
            self._scheduler.start()
            self._started = True
            logger.info("Job scheduler started")
            logger.info(f"Registered jobs: {', '.join(self.list_jobs())}")

    def stop(self):
        if self._started:
            self._scheduler.shutdown()
            self._started = False
            logger.info("Job scheduler stopped")

    def clear_jobs(self):
        self._scheduler.remove_all_jobs()
        logger.info("Cleared all scheduled jobs")


# Global scheduler instance
scheduler = JobScheduler()
