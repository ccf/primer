"""Harness intelligence endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from primer.common.database import get_db
from primer.common.schemas import DeadweightResponse
from primer.server.deps import get_auth_context

router = APIRouter(prefix="/api/v1/harness", tags=["harness"])


@router.get("/deadweight", response_model=DeadweightResponse)
def get_deadweight(
    team_id: str | None = Query(default=None),
    engineer_id: str | None = Query(default=None),
    min_sessions: int = Query(default=5, ge=1),
    db: Session = Depends(get_db),
    auth=Depends(get_auth_context),
):
    """Find customizations that are configured but add no measurable value.

    Returns items flagged as dead weight: zero-invocation customizations
    and customizations with no outcome lift versus the baseline.
    """
    from primer.server.services.deadweight_service import detect_deadweight

    items = detect_deadweight(
        db,
        team_id=team_id,
        engineer_id=engineer_id,
        min_sessions=min_sessions,
    )
    return DeadweightResponse(
        items=[
            {
                "identifier": item.identifier,
                "customization_type": item.customization_type,
                "reason": item.reason,
                "configured_sessions": item.configured_sessions,
                "invocation_count": item.invocation_count,
                "success_rate_with": item.success_rate_with,
                "success_rate_without": item.success_rate_without,
            }
            for item in items
        ],
        total_customizations_analyzed=len(items),
    )
