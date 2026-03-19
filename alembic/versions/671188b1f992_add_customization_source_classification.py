"""add customization source classification

Revision ID: 671188b1f992
Revises: 1c66d7ff642e
Create Date: 2026-03-19 17:29:49.356213

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "671188b1f992"
down_revision: Union[str, None] = "1c66d7ff642e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "session_customizations",
        sa.Column(
            "source_classification",
            sa.String(length=20),
            server_default="unknown",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("session_customizations", "source_classification")
