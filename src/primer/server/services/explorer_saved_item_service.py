from sqlalchemy.orm import Session

from primer.common.models import ExplorerSavedItem
from primer.common.schemas import ExplorerSavedItemCreate


def list_explorer_saved_items(
    db: Session,
    *,
    engineer_id: str | None,
    owner_role: str,
    item_type: str | None = None,
) -> list[ExplorerSavedItem]:
    query = db.query(ExplorerSavedItem)
    if engineer_id is not None:
        query = query.filter(ExplorerSavedItem.engineer_id == engineer_id)
    else:
        query = query.filter(
            ExplorerSavedItem.engineer_id.is_(None),
            ExplorerSavedItem.owner_role == owner_role,
        )
    if item_type:
        query = query.filter(ExplorerSavedItem.item_type == item_type)
    return query.order_by(
        ExplorerSavedItem.updated_at.desc(), ExplorerSavedItem.created_at.desc()
    ).all()


def create_explorer_saved_item(
    db: Session,
    *,
    engineer_id: str | None,
    owner_role: str,
    payload: ExplorerSavedItemCreate,
    scope_team_id: str | None,
) -> ExplorerSavedItem:
    item = ExplorerSavedItem(
        engineer_id=engineer_id,
        owner_role=owner_role,
        item_type=payload.item_type,
        title=payload.title.strip(),
        prompt_text=payload.prompt_text.strip(),
        result_preview=(payload.result_preview.strip() if payload.result_preview else None),
        scope_team_id=scope_team_id,
        scope_start_date=payload.scope_start_date,
        scope_end_date=payload.scope_end_date,
    )
    db.add(item)
    db.flush()
    return item


def delete_explorer_saved_item(
    db: Session,
    *,
    item_id: str,
    engineer_id: str | None,
    owner_role: str,
) -> ExplorerSavedItem | None:
    query = db.query(ExplorerSavedItem).filter(ExplorerSavedItem.id == item_id)
    if engineer_id is not None:
        query = query.filter(ExplorerSavedItem.engineer_id == engineer_id)
    else:
        query = query.filter(
            ExplorerSavedItem.engineer_id.is_(None),
            ExplorerSavedItem.owner_role == owner_role,
        )
    item = query.first()
    if item is None:
        return None
    db.delete(item)
    db.flush()
    return item
