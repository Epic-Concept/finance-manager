"""Create classification tables.

Revision ID: 004_create_classification_tables
Revises: 003_create_tables
Create Date: 2026-01-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_create_classification_tables"
down_revision: Union[str, None] = "003_create_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create classification-related tables."""
    # Create email_accounts table
    op.create_table(
        "email_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email_address", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("imap_server", sa.String(255), nullable=True),
        sa.Column("imap_port", sa.Integer(), nullable=False, server_default="993"),
        sa.Column("credential_reference", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email_address", name="UQ_email_accounts_email"),
        schema="finance",
    )
    op.create_index(
        "IX_email_accounts_active_priority",
        "email_accounts",
        ["is_active", "priority"],
        schema="finance",
    )

    # Create classification_rules table
    op.create_table(
        "classification_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("rule_expression", sa.Text(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "requires_disambiguation", sa.Boolean(), nullable=False, server_default="0"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["finance.categories.id"],
        ),
        schema="finance",
    )
    op.create_index(
        "IX_classification_rules_active_priority",
        "classification_rules",
        ["is_active", "priority"],
        schema="finance",
    )

    # Create category_evidence table
    op.create_table(
        "category_evidence",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("item_description", sa.String(500), nullable=False),
        sa.Column("item_price", sa.Numeric(19, 4), nullable=False),
        sa.Column("item_currency", sa.String(3), nullable=False, server_default="GBP"),
        sa.Column("item_quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("evidence_type", sa.String(50), nullable=False),
        sa.Column("email_account_id", sa.Integer(), nullable=True),
        sa.Column("email_message_id", sa.String(255), nullable=True),
        sa.Column("email_datetime", sa.DateTime(), nullable=True),
        sa.Column("evidence_summary", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("raw_extraction", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["finance.transactions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["finance.categories.id"],
        ),
        sa.ForeignKeyConstraint(
            ["email_account_id"],
            ["finance.email_accounts.id"],
        ),
        schema="finance",
    )
    op.create_index(
        "IX_category_evidence_transaction",
        "category_evidence",
        ["transaction_id"],
        schema="finance",
    )
    op.create_index(
        "IX_category_evidence_category",
        "category_evidence",
        ["category_id"],
        schema="finance",
    )
    op.create_index(
        "IX_category_evidence_email",
        "category_evidence",
        ["email_account_id", "email_message_id"],
        schema="finance",
    )


def downgrade() -> None:
    """Drop classification-related tables."""
    op.drop_table("category_evidence", schema="finance")
    op.drop_table("classification_rules", schema="finance")
    op.drop_table("email_accounts", schema="finance")
