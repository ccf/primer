"""add memory embedding column

Revision ID: 399aa5e4c5e5
Revises: ed2b38b8d95a
Create Date: 2026-06-07 23:15:59.933081

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "399aa5e4c5e5"
down_revision: Union[str, None] = "ed2b38b8d95a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # JSON variant column so create-based test DBs already have it; for an
        # existing SQLite DB, add it as a plain JSON column (no vector, no index).
        with op.batch_alter_table("memory_entries") as batch_op:
            batch_op.add_column(sa.Column("embedding", sa.JSON(), nullable=True))
        return
    # postgres + pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column("memory_entries", sa.Column("embedding", Vector(384), nullable=True))
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_memory_entries_embedding "
        "ON memory_entries USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.execute("DROP INDEX IF EXISTS ix_memory_entries_embedding")
    with op.batch_alter_table("memory_entries") as batch_op:
        batch_op.drop_column("embedding")
