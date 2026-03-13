"""add session recovery paths

Revision ID: 0f3b0a1e2c91
Revises: 6b7e5d1b8a91
Create Date: 2026-03-12 18:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0f3b0a1e2c91"
down_revision: Union[str, None] = "6b7e5d1b8a91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_recovery_paths",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("friction_detected", sa.Boolean(), nullable=False),
        sa.Column("first_friction_ordinal", sa.Integer(), nullable=True),
        sa.Column("recovery_step_count", sa.Integer(), nullable=False),
        sa.Column("recovery_strategies", sa.JSON(), nullable=True),
        sa.Column("recovery_result", sa.String(length=20), nullable=False),
        sa.Column("final_outcome", sa.String(length=50), nullable=True),
        sa.Column("last_verification_status", sa.String(length=20), nullable=True),
        sa.Column("sample_recovery_commands", sa.JSON(), nullable=True),
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
        "ix_session_recovery_paths_session_id",
        "session_recovery_paths",
        ["session_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_session_recovery_paths_session_id", table_name="session_recovery_paths")
    op.drop_table("session_recovery_paths")
