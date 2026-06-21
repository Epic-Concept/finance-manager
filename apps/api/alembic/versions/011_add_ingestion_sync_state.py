"""Add merchant_name to transactions and the sync_state cursor table.

Revision ID: 011_ingestion_sync_state
Revises: 010_classification_decisions
Create Date: 2026-06-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011_ingestion_sync_state"
down_revision: str | None = "010_classification_decisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add merchant_name and the sync_state table."""
    op.add_column(
        "transactions",
        sa.Column("merchant_name", sa.String(255), nullable=True),
        schema="finance",
    )
    op.create_table(
        "sync_state",
        sa.Column("source", sa.String(100), primary_key=True, nullable=False),
        sa.Column("cursor", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        schema="finance",
    )


def downgrade() -> None:
    """Drop the sync_state table and merchant_name column."""
    op.drop_table("sync_state", schema="finance")
    op.drop_column("transactions", "merchant_name", schema="finance")
