"""Add company_name column to job table

Revision ID: af920161464c
Revises: 085d4683e519
Create Date: 2025-08-12 01:22:22.953840

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "af920161464c"
down_revision: Union[str, Sequence[str], None] = "085d4683e519"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Add company_name column as nullable first
    op.add_column("job", sa.Column("company_name", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("job", "company_name")
