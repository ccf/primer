"""add source to review_findings unique constraint

Revision ID: 7103e4887012
Revises: a3c77ce12244
Create Date: 2026-03-07 08:49:35.231126

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "7103e4887012"
down_revision: Union[str, None] = "a3c77ce12244"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SQLITE_BATCH_NAMING_CONVENTION = {
    "uq": "uq_%(table_name)s_%(column_0_name)s",
}


def _find_unique_constraint_on_columns(table_name: str, columns: list[str]) -> str | None:
    """Return the actual constraint name for a unique constraint on the given columns."""
    bind = op.get_bind()
    inspector = inspect(bind)
    target = set(columns)
    for uc in inspector.get_unique_constraints(table_name):
        if set(uc["column_names"]) == target:
            return uc["name"]
    return None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table(
            "review_findings",
            naming_convention=SQLITE_BATCH_NAMING_CONVENTION,
        ) as batch_op:
            batch_op.drop_constraint("uq_review_findings_pull_request_id", type_="unique")
            batch_op.create_unique_constraint(
                "uq_review_findings_pr_source_ext",
                ["pull_request_id", "source", "external_id"],
            )
    else:
        # Postgres and other backends: look up the real constraint name
        existing = _find_unique_constraint_on_columns(
            "review_findings", ["pull_request_id", "external_id"]
        )
        if existing:
            op.drop_constraint(existing, "review_findings", type_="unique")
        op.create_unique_constraint(
            "uq_review_findings_pr_source_ext",
            "review_findings",
            ["pull_request_id", "source", "external_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table(
            "review_findings",
            naming_convention=SQLITE_BATCH_NAMING_CONVENTION,
        ) as batch_op:
            batch_op.drop_constraint("uq_review_findings_pr_source_ext", type_="unique")
            batch_op.create_unique_constraint(
                "uq_review_findings_pull_request_id",
                ["pull_request_id", "external_id"],
            )
    else:
        existing = _find_unique_constraint_on_columns(
            "review_findings", ["pull_request_id", "source", "external_id"]
        )
        if existing:
            op.drop_constraint(existing, "review_findings", type_="unique")
        op.create_unique_constraint(
            "uq_review_findings_pull_request_id",
            "review_findings",
            ["pull_request_id", "external_id"],
        )
