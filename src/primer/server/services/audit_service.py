from sqlalchemy.orm import Session

from primer.common.models import AuditLog
from primer.server.deps import AuthContext


def log_action(
    db: Session,
    auth: AuthContext,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=auth.engineer_id,
        actor_role=auth.role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    db.flush()
    return entry


def get_audit_logs(
    db: Session,
    resource_type: str | None = None,
    action: str | None = None,
    actor_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLog]:
    q = db.query(AuditLog)
    if resource_type:
        q = q.filter(AuditLog.resource_type == resource_type)
    if action:
        q = q.filter(AuditLog.action == action)
    if actor_id:
        q = q.filter(AuditLog.actor_id == actor_id)
    return q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
