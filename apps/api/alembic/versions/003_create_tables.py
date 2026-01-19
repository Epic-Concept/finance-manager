"""Create finance tables.

Revision ID: 003_create_tables
Revises: 002_finance_schema
Create Date: 2026-01-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_create_tables"
down_revision: Union[str, None] = "002_finance_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all finance tables."""
    # Create bank_sessions table
    op.create_table(
        "bank_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("bank_key", sa.String(100), nullable=False),
        sa.Column("bank_name", sa.String(200), nullable=False),
        sa.Column("session_id", sa.String(255), nullable=False),
        sa.Column("session_expires", sa.DateTime(), nullable=False),
        sa.Column("accounts", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bank_key"),
        schema="finance",
    )
    op.create_index(
        "IX_bank_sessions_expires",
        "bank_sessions",
        ["session_expires"],
        schema="finance",
    )

    # Create transactions table
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="GBP"),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("account_name", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="finance",
    )
    op.create_index(
        "IX_transactions_date",
        "transactions",
        ["transaction_date"],
        schema="finance",
    )
    op.create_index(
        "IX_transactions_external",
        "transactions",
        ["external_id"],
        schema="finance",
    )

    # Create online_purchases table
    op.create_table(
        "online_purchases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("shop_name", sa.String(200), nullable=False),
        sa.Column("items", sa.Text(), nullable=False),
        sa.Column("purchase_datetime", sa.DateTime(), nullable=False),
        sa.Column("price", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="GBP"),
        sa.Column("is_deferred_payment", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("transaction_id", sa.Integer(), nullable=True),
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
        schema="finance",
    )
    op.create_index(
        "IX_online_purchases_datetime",
        "online_purchases",
        ["purchase_datetime"],
        schema="finance",
    )
    op.create_index(
        "IX_online_purchases_transaction",
        "online_purchases",
        ["transaction_id"],
        schema="finance",
    )

    # Create categories table
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["finance.categories.id"],
        ),
        schema="finance",
    )

    # Create category_closure table
    # Note: SQL Server doesn't allow multiple CASCADE paths, so we use NO ACTION
    # and rely on CategoryRepository to manage closure table consistency
    op.create_table(
        "category_closure",
        sa.Column("ancestor_id", sa.Integer(), nullable=False),
        sa.Column("descendant_id", sa.Integer(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("ancestor_id", "descendant_id"),
        sa.ForeignKeyConstraint(
            ["ancestor_id"],
            ["finance.categories.id"],
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["descendant_id"],
            ["finance.categories.id"],
            ondelete="NO ACTION",
        ),
        schema="finance",
    )
    op.create_index(
        "IX_category_closure_descendant",
        "category_closure",
        ["descendant_id"],
        schema="finance",
    )

    # Create transaction_categories table
    op.create_table(
        "transaction_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_id", name="UQ_transaction_categories_transaction"),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["finance.transactions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["finance.categories.id"],
            ondelete="CASCADE",
        ),
        schema="finance",
    )
    op.create_index(
        "IX_transaction_categories_category",
        "transaction_categories",
        ["category_id"],
        schema="finance",
    )


def downgrade() -> None:
    """Drop all finance tables."""
    op.drop_table("transaction_categories", schema="finance")
    op.drop_table("category_closure", schema="finance")
    op.drop_table("categories", schema="finance")
    op.drop_table("online_purchases", schema="finance")
    op.drop_table("transactions", schema="finance")
    op.drop_table("bank_sessions", schema="finance")
