"""Explorer router — SSE streaming chat endpoint for conversational data exploration."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from primer.common.database import get_db
from primer.common.schemas import ExplorerSavedItemCreate, ExplorerSavedItemResponse
from primer.server.deps import AuthContext, get_auth_context

router = APIRouter(prefix="/api/v1/explorer", tags=["explorer"])


class ExplorerChatRequest(BaseModel):
    messages: list[dict]
    team_id: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


def _resolve_scope(
    auth: AuthContext, requested_team_id: str | None
) -> tuple[str | None, str | None]:
    """Return (team_id, engineer_id) based on role."""
    if auth.role == "admin":
        return requested_team_id, None
    if auth.role == "team_lead":
        return auth.team_id, None
    return None, auth.engineer_id


def _resolve_saved_item_scope_team_id(
    auth: AuthContext, requested_team_id: str | None
) -> str | None:
    if auth.role == "admin":
        return requested_team_id
    if auth.role == "team_lead":
        return auth.team_id
    return None


@router.post("/chat")
async def explorer_chat(
    body: ExplorerChatRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    # Note: in demo mode, DemoReadOnlyMiddleware blocks this POST before
    # it reaches the router, so no demo_mode check is needed here.
    from primer.server.services.explorer_service import stream_explorer_chat

    tid, eid = _resolve_scope(auth, body.team_id)

    return StreamingResponse(
        stream_explorer_chat(
            db=db,
            messages=body.messages,
            auth_role=auth.role,
            team_id=tid,
            engineer_id=eid,
            start_date=body.start_date,
            end_date=body.end_date,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/saved-items", response_model=list[ExplorerSavedItemResponse])
def list_saved_items(
    item_type: str | None = None,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    from primer.server.services.explorer_saved_item_service import list_explorer_saved_items

    items = list_explorer_saved_items(
        db,
        engineer_id=auth.engineer_id,
        owner_role=auth.role,
        item_type=item_type,
    )
    return [ExplorerSavedItemResponse.model_validate(item) for item in items]


@router.post("/saved-items", response_model=ExplorerSavedItemResponse)
def create_saved_item(
    payload: ExplorerSavedItemCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    from primer.server.services.explorer_saved_item_service import create_explorer_saved_item

    item = create_explorer_saved_item(
        db,
        engineer_id=auth.engineer_id,
        owner_role=auth.role,
        payload=payload,
        scope_team_id=_resolve_saved_item_scope_team_id(auth, payload.scope_team_id),
    )
    db.commit()
    db.refresh(item)
    return ExplorerSavedItemResponse.model_validate(item)


@router.delete("/saved-items/{item_id}")
def delete_saved_item(
    item_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    from primer.server.services.explorer_saved_item_service import delete_explorer_saved_item

    item = delete_explorer_saved_item(
        db,
        item_id=item_id,
        engineer_id=auth.engineer_id,
        owner_role=auth.role,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Saved item not found")
    db.commit()
    return {"status": "ok"}
