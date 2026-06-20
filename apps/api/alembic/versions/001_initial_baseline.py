"""Initial baseline migration.

Revision ID: 001_initial
Revises:
Create Date: 2026-01-19

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Initial baseline - empty schema."""
    pass


def downgrade() -> None:
    """Downgrade to nothing."""
    pass
