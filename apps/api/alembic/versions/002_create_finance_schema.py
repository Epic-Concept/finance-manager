"""Create finance schema.

Revision ID: 002_finance_schema
Revises: 001_initial
Create Date: 2026-01-19

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_finance_schema"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the finance schema."""
    op.execute("IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'finance') EXEC('CREATE SCHEMA finance')")


def downgrade() -> None:
    """Drop the finance schema."""
    op.execute("DROP SCHEMA IF EXISTS finance")
