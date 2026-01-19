"""Initial baseline migration.

Revision ID: 001_initial
Revises:
Create Date: 2026-01-19

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Initial baseline - empty schema."""
    pass


def downgrade() -> None:
    """Downgrade to nothing."""
    pass
