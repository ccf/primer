from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from primer.common.database import get_db
from primer.common.models import Engineer
from primer.common.schemas import InterventionCreate, InterventionResponse, InterventionUpdate
from primer.server.deps import AuthContext, get_auth_context
from primer.server.services.intervention_service import (
    create_intervention,
    get_intervention,
    intervention_visible_to_engineer,
    intervention_visible_to_team,
    list_interventions,
    list_interventions_for_engineer,
    update_intervention,
)

router = APIRouter(prefix="/api/v1/interventions", tags=["interventions"])

ENGINEER_SELF_EDITABLE_FIELDS = {"status", "due_date", "owner_engineer_id"}


@router.get("", response_model=list[InterventionResponse])
def interventions_list(
    team_id: str | None = None,
    engineer_id: str | None = None,
    project_name: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    if auth.role == "admin":
        return list_interventions(
            db,
            team_id=team_id,
            engineer_id=engineer_id,
            project_name=project_name,
            status=status,
        )

    if auth.role == "team_lead":
        if team_id and team_id != auth.team_id:
            raise HTTPException(status_code=403, detail="Cannot view interventions for other teams")
        if engineer_id:
            engineer = _require_engineer(db, engineer_id)
            if engineer.team_id != auth.team_id:
                raise HTTPException(status_code=403, detail="Cannot view other teams")
        return list_interventions(
            db,
            team_id=auth.team_id,
            engineer_id=engineer_id,
            project_name=project_name,
            status=status,
        )

    if engineer_id and engineer_id != auth.engineer_id:
        raise HTTPException(status_code=403, detail="Cannot view other engineers")
    interventions = list_interventions_for_engineer(db, auth.engineer_id or "", status=status)
    if project_name:
        interventions = [
            intervention
            for intervention in interventions
            if intervention.project_name == project_name
        ]
    return interventions


@router.post("", response_model=InterventionResponse, status_code=201)
def interventions_create(
    payload: InterventionCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    resolved_payload = _normalize_create_payload(db, payload, auth)
    result = create_intervention(
        db,
        resolved_payload,
        created_by_engineer_id=auth.engineer_id,
    )
    db.commit()
    return result


@router.patch("/{intervention_id}", response_model=InterventionResponse)
def interventions_update(
    intervention_id: str,
    payload: InterventionUpdate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    intervention = get_intervention(db, intervention_id)
    if intervention is None:
        raise HTTPException(status_code=404, detail="Intervention not found")
    _check_access(db, intervention, auth)

    if auth.role == "engineer":
        touched_fields = set(payload.model_dump(exclude_unset=True))
        if touched_fields - ENGINEER_SELF_EDITABLE_FIELDS:
            raise HTTPException(
                status_code=403,
                detail="Engineers can only update status, due date, or claim ownership",
            )
        if "owner_engineer_id" in touched_fields and payload.owner_engineer_id != auth.engineer_id:
            raise HTTPException(status_code=403, detail="Cannot assign to another engineer")

    if auth.role in ("team_lead", "admin"):
        _validate_team_payload(
            db,
            auth,
            payload.team_id,
            payload.engineer_id,
            payload.owner_engineer_id,
        )

    result = update_intervention(db, intervention, payload)
    db.commit()
    return result


def _normalize_create_payload(
    db: Session,
    payload: InterventionCreate,
    auth: AuthContext,
) -> InterventionCreate:
    if auth.role == "admin":
        _validate_team_payload(
            db,
            auth,
            payload.team_id,
            payload.engineer_id,
            payload.owner_engineer_id,
        )
        return payload

    if auth.role == "team_lead":
        _validate_team_payload(
            db,
            auth,
            auth.team_id,
            payload.engineer_id,
            payload.owner_engineer_id,
        )
        return payload.model_copy(update={"team_id": auth.team_id})

    engineer_id = payload.engineer_id or auth.engineer_id
    if engineer_id != auth.engineer_id:
        raise HTTPException(
            status_code=403,
            detail="Engineers can only create interventions for themselves",
        )
    owner_engineer_id = payload.owner_engineer_id or auth.engineer_id
    if owner_engineer_id != auth.engineer_id:
        raise HTTPException(
            status_code=403,
            detail="Engineers can only own their own interventions",
        )
    return payload.model_copy(
        update={
            "team_id": auth.team_id,
            "engineer_id": engineer_id,
            "owner_engineer_id": owner_engineer_id,
        }
    )


def _validate_team_payload(
    db: Session,
    auth: AuthContext,
    team_id: str | None,
    engineer_id: str | None,
    owner_engineer_id: str | None,
):
    if auth.role == "team_lead" and team_id and team_id != auth.team_id:
        raise HTTPException(status_code=403, detail="Cannot use another team's scope")

    engineer = _require_engineer(db, engineer_id) if engineer_id else None
    owner = _require_engineer(db, owner_engineer_id) if owner_engineer_id else None

    if auth.role == "team_lead":
        for record in (engineer, owner):
            if record and record.team_id != auth.team_id:
                raise HTTPException(status_code=403, detail="Cannot assign outside your team")
    if engineer and team_id and engineer.team_id and engineer.team_id != team_id:
        raise HTTPException(status_code=400, detail="Engineer scope does not match team scope")


def _check_access(db: Session, intervention, auth: AuthContext):
    if auth.role == "admin":
        return
    if auth.role == "team_lead":
        if intervention_visible_to_team(db, intervention, auth.team_id or ""):
            return
        raise HTTPException(status_code=403, detail="Cannot access another team's intervention")
    if intervention_visible_to_engineer(intervention, auth.engineer_id or ""):
        return
    raise HTTPException(status_code=403, detail="Cannot access another engineer's intervention")


def _require_engineer(db: Session, engineer_id: str) -> Engineer:
    engineer = db.query(Engineer).filter(Engineer.id == engineer_id).first()
    if engineer is None:
        raise HTTPException(status_code=404, detail="Engineer not found")
    return engineer
