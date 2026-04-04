"""add engineer api key lookup hash

Revision ID: c2f8b3a91d4e
Revises: 5d4c1c9b2a0f
Create Date: 2026-04-04 13:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2f8b3a91d4e"
down_revision: Union[str, None] = "5d4c1c9b2a0f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "engineers",
        sa.Column("api_key_lookup_hash", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_engineers_api_key_lookup_hash",
        "engineers",
        ["api_key_lookup_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_engineers_api_key_lookup_hash", table_name="engineers")
    op.drop_column("engineers", "api_key_lookup_hash")
