"""add explorer saved items

Revision ID: 9c4e71d3b2a1
Revises: 8f1d9f8c1b8a
Create Date: 2026-04-05 18:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c4e71d3b2a1"
down_revision: Union[str, None] = "8f1d9f8c1b8a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "explorer_saved_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("engineer_id", sa.String(length=36), nullable=True),
        sa.Column("owner_role", sa.String(length=20), nullable=False),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("result_preview", sa.Text(), nullable=True),
        sa.Column("scope_team_id", sa.String(length=36), nullable=True),
        sa.Column("scope_start_date", sa.DateTime(), nullable=True),
        sa.Column("scope_end_date", sa.DateTime(), nullable=True),
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
        sa.ForeignKeyConstraint(["engineer_id"], ["engineers.id"]),
        sa.ForeignKeyConstraint(["scope_team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_explorer_saved_items_engineer_created",
        "explorer_saved_items",
        ["engineer_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_explorer_saved_items_role_created",
        "explorer_saved_items",
        ["owner_role", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_explorer_saved_items_role_created", table_name="explorer_saved_items")
    op.drop_index("ix_explorer_saved_items_engineer_created", table_name="explorer_saved_items")
    op.drop_table("explorer_saved_items")
