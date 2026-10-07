from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.report import AuditLogItem
from app.security.dependencies import require_roles


router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])
admin_user = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)


@router.get("", response_model=list[AuditLogItem])
def list_audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(admin_user),
) -> list[dict]:
    logs = db.scalars(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(max(limit, 1), 500))
    ).all()
    return [
        {
            "id": log.id,
            "actor": f"{log.user.first_name} {log.user.last_name}" if log.user else None,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "description": log.description,
            "created_at": log.created_at,
        }
        for log in logs
    ]