"""add session source metadata

Revision ID: 8f1d9f8c1b8a
Revises: c2f8b3a91d4e
Create Date: 2026-04-04 14:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f1d9f8c1b8a"
down_revision: Union[str, None] = "c2f8b3a91d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("source_metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "source_metadata")
