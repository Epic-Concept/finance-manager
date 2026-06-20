"""Add confirmed flag to classification_decisions.

Revision ID: 012_decision_confirmed
Revises: 011_ingestion_sync_state
Create Date: 2026-06-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012_decision_confirmed"
down_revision: str | None = "011_ingestion_sync_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the confirmed column (human-confirmed decisions feed STRONG history)."""
    op.add_column(
        "classification_decisions",
        sa.Column(
            "confirmed", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        schema="finance",
    )


def downgrade() -> None:
    """Drop the confirmed column."""
    op.drop_column("classification_decisions", "confirmed", schema="finance")
