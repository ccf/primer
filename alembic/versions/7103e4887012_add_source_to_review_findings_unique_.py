"""add source to review_findings unique constraint

Revision ID: 7103e4887012
Revises: a3c77ce12244
Create Date: 2026-03-07 08:49:35.231126

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "7103e4887012"
down_revision: Union[str, None] = "a3c77ce12244"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SQLITE_BATCH_NAMING_CONVENTION = {
    "uq": "uq_%(table_name)s_%(column_0_name)s",
}


def upgrade() -> None:
    with op.batch_alter_table(
        "review_findings",
        naming_convention=SQLITE_BATCH_NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint("uq_review_findings_pull_request_id", type_="unique")
        batch_op.create_unique_constraint(
            "uq_review_findings_pr_source_ext",
            ["pull_request_id", "source", "external_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "review_findings",
        naming_convention=SQLITE_BATCH_NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint("uq_review_findings_pr_source_ext", type_="unique")
        batch_op.create_unique_constraint(
            "uq_review_findings_pull_request_id",
            ["pull_request_id", "external_id"],
        )
