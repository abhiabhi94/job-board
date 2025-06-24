import sqlalchemy as sa

from job_board.connection import get_session
from job_board.models import BaseModel
from job_board.portals.base import PORTALS


class PortalSetting(BaseModel):
    __tablename__ = "portal_setting"

    portal_name = sa.Column(sa.String, nullable=False)
    last_run_at = sa.Column(sa.DateTime)

    __table_args__ = (
        sa.Index(
            "ix_portal_name_lower",
            sa.func.lower(portal_name),
            unique=True,
        ),
    )

    @classmethod
    def get_or_create(cls, portal_name: str) -> "PortalSetting":
        if portal_name not in PORTALS:
            raise ValueError(f"Portal {portal_name} is not supported")

        with get_session(readonly=False) as session:
            setting = (
                session.query(PortalSetting)
                .filter(sa.func.lower(PortalSetting.portal_name) == portal_name)
                .one_or_none()
            )
            if setting is None:
                setting = PortalSetting(portal_name=portal_name)
                session.add(setting)
                # this is needed to get the id of the newly
                # created setting object.
                session.flush()
        return setting
