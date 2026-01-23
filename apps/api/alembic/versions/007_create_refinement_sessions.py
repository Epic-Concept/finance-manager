"""Create refinement session tables for interactive rule refinement.

Revision ID: 007_create_refinement_sessions
Revises: 006_create_rule_proposals
Create Date: 2026-01-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007_create_refinement_sessions"
down_revision: Union[str, None] = "006_create_rule_proposals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create refinement_sessions, session_messages, and session_rule_proposals tables."""
    # Create refinement_sessions table
    op.create_table(
        "refinement_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cluster_hash", sa.String(64), nullable=False),
        sa.Column("cluster_key", sa.String(100), nullable=False),
        sa.Column("cluster_size", sa.Integer(), nullable=False),
        sa.Column("sample_descriptions", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="active"
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="finance",
    )
    op.create_index(
        "IX_refinement_sessions_cluster_hash",
        "refinement_sessions",
        ["cluster_hash"],
        schema="finance",
    )
    op.create_index(
        "IX_refinement_sessions_status",
        "refinement_sessions",
        ["status"],
        schema="finance",
    )

    # Create session_messages table
    op.create_table(
        "session_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("proposed_rules_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["finance.refinement_sessions.id"],
            ondelete="CASCADE",
        ),
        schema="finance",
    )
    op.create_index(
        "IX_session_messages_session_id",
        "session_messages",
        ["session_id"],
        schema="finance",
    )

    # Create session_rule_proposals table
    op.create_table(
        "session_rule_proposals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("proposed_pattern", sa.String(500), nullable=False),
        sa.Column("proposed_category_id", sa.Integer(), nullable=False),
        sa.Column("llm_confidence", sa.String(20), nullable=False),
        sa.Column("llm_reasoning", sa.Text(), nullable=False),
        sa.Column("validation_matches", sa.Integer(), nullable=True),
        sa.Column("validation_true_positives", sa.Integer(), nullable=True),
        sa.Column("validation_false_positives", sa.Integer(), nullable=True),
        sa.Column("validation_precision", sa.Numeric(5, 4), nullable=True),
        sa.Column("validation_coverage", sa.Numeric(5, 4), nullable=True),
        sa.Column("validation_false_positives_json", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="pending"
        ),
        sa.Column("final_rule_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["finance.refinement_sessions.id"],
            ondelete="CASCADE",
        ),
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
        "IX_session_rule_proposals_session_id",
        "session_rule_proposals",
        ["session_id"],
        schema="finance",
    )
    op.create_index(
        "IX_session_rule_proposals_status",
        "session_rule_proposals",
        ["status"],
        schema="finance",
    )


def downgrade() -> None:
    """Drop refinement session tables."""
    op.drop_table("session_rule_proposals", schema="finance")
    op.drop_table("session_messages", schema="finance")
    op.drop_table("refinement_sessions", schema="finance")
