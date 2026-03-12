"""add session change shapes

Revision ID: 6b7e5d1b8a91
Revises: 3a8722751e66
Create Date: 2026-03-12 16:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6b7e5d1b8a91"
down_revision: Union[str, None] = "3a8722751e66"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_change_shapes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("files_touched_count", sa.Integer(), nullable=False),
        sa.Column("named_touched_files", sa.JSON(), nullable=True),
        sa.Column("commit_files_changed", sa.Integer(), nullable=False),
        sa.Column("lines_added", sa.Integer(), nullable=False),
        sa.Column("lines_deleted", sa.Integer(), nullable=False),
        sa.Column("diff_size", sa.Integer(), nullable=False),
        sa.Column("edit_operations", sa.Integer(), nullable=False),
        sa.Column("create_operations", sa.Integer(), nullable=False),
        sa.Column("delete_operations", sa.Integer(), nullable=False),
        sa.Column("rename_operations", sa.Integer(), nullable=False),
        sa.Column("churn_files_count", sa.Integer(), nullable=False),
        sa.Column("rewrite_indicator", sa.Boolean(), nullable=False),
        sa.Column("revert_indicator", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_session_change_shapes_session_id",
        "session_change_shapes",
        ["session_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_session_change_shapes_session_id", table_name="session_change_shapes")
    op.drop_table("session_change_shapes")
