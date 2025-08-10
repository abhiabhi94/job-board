import pycountry
import sqlalchemy as sa

from job_board.connection import get_engine
from job_board.connection import get_session
from job_board.logger import logger
from job_board.models import BaseModel


def init_db():
    """
    Initialize the database by creating all tables and setting up initial data.
    """
    logger.info("Creating Tables")
    engine = get_engine()
    BaseModel.metadata.create_all(bind=engine)

    # Setup location validation after tables are created
    _setup_location_validation(engine)


def _setup_location_validation(engine):
    """Setup location validation lookup table and populate with ISO codes"""
    logger.info("Setting up location validation")

    with get_session(readonly=False) as session:
        # Create lookup table (idempotent)
        session.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS valid_location_codes (
                    code VARCHAR(10) PRIMARY KEY
                )
                """
            )
        )

        # Populate with ISO codes
        valid_codes = []

        # Add all ISO 3166-1 country codes
        for country in pycountry.countries:
            valid_codes.append(country.alpha_2)

        # Add all ISO 3166-2 subdivision codes
        for subdivision in pycountry.subdivisions:
            valid_codes.append(subdivision.code)

        values_clause = ",".join(f"('{code}')" for code in valid_codes)
        session.execute(
            sa.text(
                f"""
                INSERT INTO valid_location_codes (code)
                VALUES {values_clause}
                ON CONFLICT DO NOTHING
                """
            )
        )

    logger.info(
        f"Location validation setup complete. {len(valid_codes)} valid codes available."
    )
