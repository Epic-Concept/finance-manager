"""Add category commitment fields.

Revision ID: 005_add_category_fields
Revises: 004_create_classification_tables
Create Date: 2026-01-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_add_category_fields"
down_revision: Union[str, None] = "004_create_classification_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add commitment_level, frequency, and is_essential columns to categories."""
    op.add_column(
        "categories",
        sa.Column("commitment_level", sa.Integer(), nullable=True),
        schema="finance",
    )
    op.add_column(
        "categories",
        sa.Column("frequency", sa.String(20), nullable=True),
        schema="finance",
    )
    op.add_column(
        "categories",
        sa.Column("is_essential", sa.Boolean(), nullable=False, server_default="0"),
        schema="finance",
    )


def downgrade() -> None:
    """Remove commitment_level, frequency, and is_essential columns from categories."""
    op.drop_column("categories", "is_essential", schema="finance")
    op.drop_column("categories", "frequency", schema="finance")
    op.drop_column("categories", "commitment_level", schema="finance")
