from sqlalchemy import Column, Integer, String, DateTime, func, Index


from job_board.models import BaseModel
from job_board.portals.base import PORTALS
from job_board.connection import get_session


class PortalSetting(BaseModel):
    __tablename__ = "portal_setting"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portal_name = Column(String, nullable=False)
    last_run_at = Column(DateTime)

    __table_args__ = (
        Index(
            "ix_portal_name_lower",
            func.lower(portal_name),
            unique=True,
        ),
    )

    @classmethod
    def get_or_create(cls, portal_name: str) -> "PortalSetting":
        if portal_name not in PORTALS:
            raise ValueError(f"Portal {portal_name} is not supported")

        session = get_session(readonly=False)
        with session:
            setting = (
                session.query(PortalSetting)
                .filter(PortalSetting.portal_name == portal_name)
                .one_or_none()
            )
            if setting is None:
                setting = PortalSetting(portal_name=portal_name)
                session.add(setting)
                # this is needed to get the id of the newly
                # created setting object.
                session.flush()
        return setting
