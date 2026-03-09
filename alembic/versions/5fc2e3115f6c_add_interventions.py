"""add interventions

Revision ID: 5fc2e3115f6c
Revises: 4c9f2f8c1d6a
Create Date: 2026-03-09 15:25:55.878541

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5fc2e3115f6c"
down_revision: Union[str, None] = "4c9f2f8c1d6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "interventions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("team_id", sa.String(length=36), nullable=True),
        sa.Column("engineer_id", sa.String(length=36), nullable=True),
        sa.Column("owner_engineer_id", sa.String(length=36), nullable=True),
        sa.Column("created_by_engineer_id", sa.String(length=36), nullable=True),
        sa.Column("project_name", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), server_default="info", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="planned", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=True),
        sa.Column("source_title", sa.String(length=255), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("baseline_start_at", sa.DateTime(), nullable=True),
        sa.Column("baseline_end_at", sa.DateTime(), nullable=True),
        sa.Column("baseline_metrics", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_engineer_id"],
            ["engineers.id"],
        ),
        sa.ForeignKeyConstraint(
            ["engineer_id"],
            ["engineers.id"],
        ),
        sa.ForeignKeyConstraint(
            ["owner_engineer_id"],
            ["engineers.id"],
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_interventions_engineer_status", "interventions", ["engineer_id", "status"], unique=False
    )
    op.create_index(
        "ix_interventions_owner_status",
        "interventions",
        ["owner_engineer_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_interventions_team_status", "interventions", ["team_id", "status"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_interventions_team_status", table_name="interventions")
    op.drop_index("ix_interventions_owner_status", table_name="interventions")
    op.drop_index("ix_interventions_engineer_status", table_name="interventions")
    op.drop_table("interventions")
