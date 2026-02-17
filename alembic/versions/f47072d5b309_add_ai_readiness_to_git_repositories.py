"""add ai readiness to git repositories

Revision ID: f47072d5b309
Revises: 7752efb0e9d2
Create Date: 2026-02-16 20:08:11.915281

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f47072d5b309"
down_revision: Union[str, None] = "7752efb0e9d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("git_repositories") as batch_op:
        batch_op.add_column(sa.Column("has_claude_md", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("has_agents_md", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("has_claude_dir", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("ai_readiness_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("ai_readiness_checked_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("git_repositories") as batch_op:
        batch_op.drop_column("ai_readiness_checked_at")
        batch_op.drop_column("ai_readiness_score")
        batch_op.drop_column("has_claude_dir")
        batch_op.drop_column("has_agents_md")
        batch_op.drop_column("has_claude_md")
