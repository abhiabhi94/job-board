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
    def create_portal_setting(cls):
        session = get_session()
        with session.begin():
            existing_settings = session.query(cls).all()
            portals = set(PORTALS.keys()) - {s.portal_name for s in existing_settings}
            session.add_all(cls(portal_name=p) for p in portals)
