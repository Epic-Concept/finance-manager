"""Create rule_proposals table.

Revision ID: 006_create_rule_proposals
Revises: 005_add_category_commitment_fields
Create Date: 2026-01-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_create_rule_proposals"
down_revision: Union[str, None] = "005_add_category_commitment_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create rule_proposals table for tracking LLM-proposed classification rules."""
    op.create_table(
        "rule_proposals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cluster_hash", sa.String(64), nullable=False),
        sa.Column("cluster_size", sa.Integer(), nullable=False),
        sa.Column("sample_descriptions", sa.Text(), nullable=False),
        sa.Column("proposed_pattern", sa.String(500), nullable=True),
        sa.Column("proposed_category_id", sa.Integer(), nullable=True),
        sa.Column("llm_confidence", sa.String(20), nullable=True),
        sa.Column("llm_reasoning", sa.Text(), nullable=True),
        sa.Column("validation_matches", sa.Integer(), nullable=True),
        sa.Column("validation_precision", sa.Numeric(5, 4), nullable=True),
        sa.Column("validation_false_positives", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="pending"
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("final_rule_id", sa.Integer(), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["proposed_category_id"],
            ["finance.categories.id"],
        ),
        sa.ForeignKeyConstraint(
            ["final_rule_id"],
            ["finance.classification_rules.id"],
        ),
        schema="finance",
    )
    op.create_index(
        "IX_rule_proposals_status",
        "rule_proposals",
        ["status"],
        schema="finance",
    )
    op.create_index(
        "IX_rule_proposals_cluster_hash",
        "rule_proposals",
        ["cluster_hash"],
        schema="finance",
    )


def downgrade() -> None:
    """Drop rule_proposals table."""
    op.drop_table("rule_proposals", schema="finance")
