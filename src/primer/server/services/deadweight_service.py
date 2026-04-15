"""Dead weight detection for agent harness configurations.

Identifies customizations (MCPs, skills, commands, subagents) that are
configured but unused, or that don't improve outcomes. Surfaces the
"what can you stop doing?" insight from the harness intelligence thesis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import func

from primer.common.facet_taxonomy import is_success_outcome
from primer.common.models import Session as SessionModel
from primer.common.models import (
    SessionCustomization,
    SessionFacets,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class DeadweightItem:
    """A customization flagged as potential dead weight."""

    identifier: str
    customization_type: str
    reason: str  # "unused", "no_outcome_lift", "zero_invocations"
    configured_sessions: int
    invocation_count: int
    success_rate_with: float | None
    success_rate_without: float | None


def detect_deadweight(
    db: Session,
    *,
    team_id: str | None = None,
    engineer_id: str | None = None,
    min_sessions: int = 5,
) -> tuple[list[DeadweightItem], int]:
    """Find customizations that are configured but add no measurable value.

    Flags:
    1. Zero-invocation customizations (configured but never used)
    2. Customizations with no outcome lift (success rate WITH <= WITHOUT)

    Requires at least `min_sessions` with the customization to avoid
    flagging rarely-seen items on insufficient data.

    Returns (flagged_items, total_customizations_analyzed).
    """
    from primer.common.models import Engineer

    # Build base session filter
    base_q = db.query(SessionModel.id)
    if engineer_id:
        base_q = base_q.filter(SessionModel.engineer_id == engineer_id)
    elif team_id:
        base_q = base_q.join(Engineer).filter(Engineer.team_id == team_id)
    session_ids = base_q.subquery()

    # Get all customizations across matching sessions (with min_sessions threshold)
    customization_rows = (
        db.query(
            SessionCustomization.identifier,
            SessionCustomization.customization_type,
            func.count(SessionCustomization.session_id.distinct()).label("session_count"),
            func.sum(SessionCustomization.invocation_count).label("total_invocations"),
        )
        .filter(SessionCustomization.session_id.in_(db.query(session_ids.c.id)))
        .group_by(SessionCustomization.identifier, SessionCustomization.customization_type)
        .having(func.count(SessionCustomization.session_id.distinct()) >= min_sessions)
        .all()
    )

    total_analyzed = len(customization_rows)
    if not customization_rows:
        return [], 0

    items: list[DeadweightItem] = []

    for row in customization_rows:
        identifier = row.identifier
        ctype = row.customization_type
        session_count = int(row.session_count)
        total_invocations = int(row.total_invocations or 0)

        # Sessions WITH this customization
        sessions_with = (
            db.query(SessionCustomization.session_id)
            .filter(
                SessionCustomization.session_id.in_(db.query(session_ids.c.id)),
                SessionCustomization.identifier == identifier,
                SessionCustomization.customization_type == ctype,
            )
            .subquery()
        )

        # Flag 1: zero invocations
        if total_invocations == 0:
            # Compute true counterfactual: success rate for sessions WITHOUT
            outcomes_without = (
                db.query(SessionFacets.outcome)
                .filter(
                    SessionFacets.session_id.in_(db.query(session_ids.c.id)),
                    ~SessionFacets.session_id.in_(db.query(sessions_with.c.session_id)),
                    SessionFacets.outcome.isnot(None),
                )
                .all()
            )
            count_without = len(outcomes_without)
            success_without = sum(1 for (o,) in outcomes_without if is_success_outcome(o))
            rate_without = success_without / count_without if count_without else None

            items.append(
                DeadweightItem(
                    identifier=identifier,
                    customization_type=ctype,
                    reason="zero_invocations",
                    configured_sessions=session_count,
                    invocation_count=0,
                    success_rate_with=None,
                    success_rate_without=round(rate_without, 3)
                    if rate_without is not None
                    else None,
                )
            )
            continue

        # Flag 2: no outcome lift
        # Success rate for sessions WITH this customization
        outcomes_with = (
            db.query(SessionFacets.outcome)
            .filter(
                SessionFacets.session_id.in_(db.query(sessions_with.c.session_id)),
                SessionFacets.outcome.isnot(None),
            )
            .all()
        )
        count_with = len(outcomes_with)
        success_with = sum(1 for (o,) in outcomes_with if is_success_outcome(o))
        rate_with = success_with / count_with if count_with >= min_sessions else None

        # True counterfactual: success rate for sessions WITHOUT this customization
        outcomes_without = (
            db.query(SessionFacets.outcome)
            .filter(
                SessionFacets.session_id.in_(db.query(session_ids.c.id)),
                ~SessionFacets.session_id.in_(db.query(sessions_with.c.session_id)),
                SessionFacets.outcome.isnot(None),
            )
            .all()
        )
        count_without = len(outcomes_without)
        success_without = sum(1 for (o,) in outcomes_without if is_success_outcome(o))
        rate_without = success_without / count_without if count_without >= min_sessions else None

        if rate_with is not None and rate_without is not None and rate_with <= rate_without:
            items.append(
                DeadweightItem(
                    identifier=identifier,
                    customization_type=ctype,
                    reason="no_outcome_lift",
                    configured_sessions=session_count,
                    invocation_count=total_invocations,
                    success_rate_with=round(rate_with, 3),
                    success_rate_without=round(rate_without, 3),
                )
            )

    return sorted(items, key=lambda x: x.configured_sessions, reverse=True), total_analyzed
