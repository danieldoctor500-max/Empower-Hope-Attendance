from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


def record_audit(
	db: Session,
	actor: User | None,
	action: str,
	entity_type: str,
	entity_id: int | None,
	description: str,
	*,
	old_values: dict[str, Any] | None = None,
	new_values: dict[str, Any] | None = None,
	ip_address: str | None = None,
) -> None:
	db.add(
		AuditLog(
			user_id=actor.id if actor else None,
			action=action,
			entity_type=entity_type,
			entity_id=entity_id,
			description=description,
			old_values=old_values,
			new_values=new_values,
			ip_address=ip_address,
		)
	)
