"""add agent_type, rename claude_version and claude_helpfulness

Revision ID: a1b2c3d4e5f6
Revises: 7dda515efd1d
Create Date: 2026-02-27 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "7dda515efd1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- sessions table ---
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.add_column(
            sa.Column("agent_type", sa.String(30), nullable=False, server_default="claude_code")
        )
        batch_op.alter_column("claude_version", new_column_name="agent_version")
        batch_op.create_index("ix_sessions_agent_type", ["agent_type"])

    # --- session_facets table ---
    with op.batch_alter_table("session_facets") as batch_op:
        batch_op.alter_column("claude_helpfulness", new_column_name="agent_helpfulness")

    # --- daily_stats table ---
    with op.batch_alter_table("daily_stats") as batch_op:
        batch_op.add_column(
            sa.Column("agent_type", sa.String(30), nullable=False, server_default="claude_code")
        )
        batch_op.drop_constraint("uq_daily_stats_engineer_date")
        batch_op.create_unique_constraint(
            "uq_daily_stats_engineer_date", ["engineer_id", "date", "agent_type"]
        )


def downgrade() -> None:
    # --- daily_stats table ---
    with op.batch_alter_table("daily_stats") as batch_op:
        batch_op.drop_constraint("uq_daily_stats_engineer_date")
        batch_op.create_unique_constraint("uq_daily_stats_engineer_date", ["engineer_id", "date"])
        batch_op.drop_column("agent_type")

    # --- session_facets table ---
    with op.batch_alter_table("session_facets") as batch_op:
        batch_op.alter_column("agent_helpfulness", new_column_name="claude_helpfulness")

    # --- sessions table ---
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.drop_index("ix_sessions_agent_type")
        batch_op.alter_column("agent_version", new_column_name="claude_version")
        batch_op.drop_column("agent_type")
