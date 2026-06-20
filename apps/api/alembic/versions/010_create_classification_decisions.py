"""Create classification decision, split, and evidence tables.

Revision ID: 010_create_classification_decisions
Revises: 009_add_proposed_category_name
Create Date: 2026-06-18

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010_classification_decisions"
down_revision: str | None = "009_add_proposed_category_name"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the evidence-driven classification decision tables."""
    op.create_table(
        "classification_decisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("merchant_class", sa.String(20), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["finance.transactions.id"]
        ),
        schema="finance",
    )
    op.create_index(
        "IX_classification_decisions_transaction",
        "classification_decisions",
        ["transaction_id"],
        schema="finance",
    )
    op.create_index(
        "IX_classification_decisions_outcome",
        "classification_decisions",
        ["outcome"],
        schema="finance",
    )

    op.create_table(
        "categorization_splits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("decision_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["decision_id"], ["finance.classification_decisions.id"]
        ),
        sa.ForeignKeyConstraint(["category_id"], ["finance.categories.id"]),
        schema="finance",
    )
    op.create_index(
        "IX_categorization_splits_decision",
        "categorization_splits",
        ["decision_id"],
        schema="finance",
    )
    op.create_index(
        "IX_categorization_splits_category",
        "categorization_splits",
        ["category_id"],
        schema="finance",
    )

    op.create_table(
        "decision_evidence",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("decision_id", sa.Integer(), nullable=False),
        sa.Column("evidence_type", sa.String(30), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("itemized", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["decision_id"], ["finance.classification_decisions.id"]
        ),
        schema="finance",
    )
    op.create_index(
        "IX_decision_evidence_decision",
        "decision_evidence",
        ["decision_id"],
        schema="finance",
    )


def downgrade() -> None:
    """Drop the evidence-driven classification decision tables."""
    op.drop_table("decision_evidence", schema="finance")
    op.drop_table("categorization_splits", schema="finance")
    op.drop_table("classification_decisions", schema="finance")
