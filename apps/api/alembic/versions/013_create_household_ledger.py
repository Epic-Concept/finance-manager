"""Create ledger tables: pockets, journal_entries, postings.

Revision ID: 013_household_ledger
Revises: 012_decision_confirmed
Create Date: 2026-08-20

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "013_household_ledger"
down_revision: str | None = "012_decision_confirmed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pockets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("account_name", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_name", name="UQ_pockets_account_name"),
        schema="finance",
    )
    op.create_index("IX_pockets_kind", "pockets", ["kind"], schema="finance")

    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("decision_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("reversed_entry_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["transaction_id"], ["finance.transactions.id"]),
        sa.ForeignKeyConstraint(
            ["decision_id"], ["finance.classification_decisions.id"]
        ),
        sa.ForeignKeyConstraint(
            ["reversed_entry_id"], ["finance.journal_entries.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="finance",
    )
    op.create_index(
        "IX_journal_entries_transaction",
        "journal_entries",
        ["transaction_id"],
        schema="finance",
    )
    op.create_index(
        "IX_journal_entries_decision",
        "journal_entries",
        ["decision_id"],
        schema="finance",
    )

    op.create_table(
        "postings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("pocket_id", sa.Integer(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "(pocket_id IS NOT NULL AND category_id IS NULL) OR "
            "(pocket_id IS NULL AND category_id IS NOT NULL)",
            name="CK_postings_pocket_xor_nominal",
        ),
        sa.ForeignKeyConstraint(["entry_id"], ["finance.journal_entries.id"]),
        sa.ForeignKeyConstraint(["pocket_id"], ["finance.pockets.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["finance.categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="finance",
    )
    op.create_index("IX_postings_entry", "postings", ["entry_id"], schema="finance")
    op.create_index("IX_postings_pocket", "postings", ["pocket_id"], schema="finance")
    op.create_index(
        "IX_postings_category", "postings", ["category_id"], schema="finance"
    )


def downgrade() -> None:
    op.drop_table("postings", schema="finance")
    op.drop_table("journal_entries", schema="finance")
    op.drop_table("pockets", schema="finance")
