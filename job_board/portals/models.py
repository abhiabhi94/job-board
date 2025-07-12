from datetime import timedelta
from datetime import timezone

import sqlalchemy as sa

from job_board.connection import get_session
from job_board.models import BaseModel
from job_board.models import store_jobs
from job_board.portals.base import PORTALS
from job_board.utils import utcnow_naive


class Portal(BaseModel):
    __tablename__ = "portal"

    name = sa.Column(sa.String, nullable=False)
    last_run_at = sa.Column(sa.DateTime)

    __table_args__ = (
        sa.Index(
            "ix_name_lower",
            sa.func.lower(name),
            unique=True,
        ),
    )

    @classmethod
    def get_or_create(cls, name: str) -> "Portal":
        if name not in PORTALS:
            raise ValueError(f"Portal {name} is not supported")

        with get_session(readonly=False) as session:
            portal = (
                session.query(Portal)
                .filter(sa.func.lower(Portal.name) == name)
                .one_or_none()
            )
            if portal is None:
                portal = Portal(name=name)
                session.add(portal)
                # this is needed to get the id of the newly
                # created setting object.
                session.flush()
        return portal

    @classmethod
    def fetch_jobs(cls, name: str) -> None:
        if name not in PORTALS:
            raise ValueError(f"Portal {name} is not supported")

        portal = cls.get_or_create(name)
        portal_id = portal.id
        last_run_at = portal.last_run_at
        if portal.last_run_at:
            last_run_at = portal.last_run_at.astimezone(timezone.utc)
            # just to have a buffer
            last_run_at -= timedelta(minutes=5)

        portal_class = PORTALS[name]
        portal_obj = portal_class(last_run_at=last_run_at)
        jobs = portal_obj.fetch_jobs()

        store_jobs(jobs)

        with get_session(readonly=False) as session:
            portal = session.get(Portal, portal_id)
            portal.last_run_at = utcnow_naive()
