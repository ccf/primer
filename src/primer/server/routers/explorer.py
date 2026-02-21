"""Explorer router — SSE streaming chat endpoint for conversational data exploration."""

from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from primer.common.database import get_db
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


@router.post("/chat")
async def explorer_chat(
    body: ExplorerChatRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
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
