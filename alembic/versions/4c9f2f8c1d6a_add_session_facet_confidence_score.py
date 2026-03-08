"""add confidence_score to session_facets

Revision ID: 4c9f2f8c1d6a
Revises: 7103e4887012
Create Date: 2026-03-07 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4c9f2f8c1d6a"
down_revision: Union[str, None] = "7103e4887012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("session_facets") as batch_op:
        batch_op.add_column(sa.Column("confidence_score", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("session_facets") as batch_op:
        batch_op.drop_column("confidence_score")
