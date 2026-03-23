"""add intervention experiment fields

Revision ID: 96ad815a1a77
Revises: 671188b1f992
Create Date: 2026-03-23 10:31:44.779427

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "96ad815a1a77"
down_revision: Union[str, None] = "671188b1f992"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "interventions", sa.Column("experiment_type", sa.String(length=50), nullable=True)
    )
    op.add_column("interventions", sa.Column("experiment_hypothesis", sa.Text(), nullable=True))
    op.add_column(
        "interventions",
        sa.Column("experiment_target_cohort", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "interventions",
        sa.Column("experiment_success_criteria", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("interventions", "experiment_success_criteria")
    op.drop_column("interventions", "experiment_target_cohort")
    op.drop_column("interventions", "experiment_hypothesis")
    op.drop_column("interventions", "experiment_type")
