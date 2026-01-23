"""Add classification tracking columns to transaction_categories.

Revision ID: 008_add_classification_tracking
Revises: 007_create_refinement_sessions
Create Date: 2026-01-23
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "008_add_classification_tracking"
down_revision = "007_create_refinement_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add classification_source and classification_rule_id to transaction_categories."""
    op.add_column(
        "transaction_categories",
        sa.Column("classification_source", sa.String(50), nullable=True),
        schema="finance",
    )
    op.add_column(
        "transaction_categories",
        sa.Column("classification_rule_id", sa.Integer(), nullable=True),
        schema="finance",
    )
    op.create_foreign_key(
        "FK_transaction_categories_rule",
        "transaction_categories",
        "classification_rules",
        ["classification_rule_id"],
        ["id"],
        source_schema="finance",
        referent_schema="finance",
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove classification tracking columns."""
    op.drop_constraint(
        "FK_transaction_categories_rule",
        "transaction_categories",
        schema="finance",
        type_="foreignkey",
    )
    op.drop_column("transaction_categories", "classification_rule_id", schema="finance")
    op.drop_column("transaction_categories", "classification_source", schema="finance")
