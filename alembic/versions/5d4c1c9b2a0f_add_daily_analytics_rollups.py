"""add daily analytics rollups

Revision ID: 5d4c1c9b2a0f
Revises: f87d66ab973b
Create Date: 2026-04-02 01:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5d4c1c9b2a0f"
down_revision: Union[str, None] = "f87d66ab973b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_analytics_rollups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("scope_key", sa.String(length=255), nullable=False),
        sa.Column("team_id", sa.String(length=36), nullable=True),
        sa.Column("session_count", sa.Integer(), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False),
        sa.Column("tool_call_count", sa.Integer(), nullable=False),
        sa.Column("success_session_count", sa.Integer(), nullable=False),
        sa.Column("outcome_session_count", sa.Integer(), nullable=False),
        sa.Column(
            "refreshed_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date", "scope_key", name="uq_daily_analytics_rollups_date_scope"),
    )
    op.create_index(
        "ix_daily_analytics_rollups_team_date",
        "daily_analytics_rollups",
        ["team_id", "date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_daily_analytics_rollups_team_date", table_name="daily_analytics_rollups")
    op.drop_table("daily_analytics_rollups")
