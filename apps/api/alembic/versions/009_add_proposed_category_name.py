"""Add proposed_category_name column to session_rule_proposals.

Revision ID: 009_add_proposed_category_name
Revises: 008_add_classification_tracking
Create Date: 2026-01-25
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "009_add_proposed_category_name"
down_revision = "008_add_classification_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add proposed_category_name column to session_rule_proposals."""
    op.add_column(
        "session_rule_proposals",
        sa.Column(
            "proposed_category_name", sa.String(100), nullable=False, server_default="Unknown"
        ),
        schema="finance",
    )
    # Remove server_default after adding column
    op.alter_column(
        "session_rule_proposals",
        "proposed_category_name",
        server_default=None,
        schema="finance",
    )


def downgrade() -> None:
    """Remove proposed_category_name column from session_rule_proposals."""
    op.drop_column("session_rule_proposals", "proposed_category_name", schema="finance")
