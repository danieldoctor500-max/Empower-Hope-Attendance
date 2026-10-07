from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.class_model import Class
from app.models.enums import SessionStatus, SessionType, UserRole
from app.models.session import AttendanceSession
from app.models.user import User
from app.permissions.access_control import is_admin, require_class_access
from app.schemas.session import AttendanceSessionCreate, AttendanceSessionResponse, AttendanceSessionUpdate
from app.core.dependencies import get_current_user, require_roles
from app.services.audit_service import record_audit
from app.services.session_service import get_session, list_accessible_sessions


router = APIRouter(prefix="/sessions", tags=["Sessions"])
admin_user = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
session_manager = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.STAFF)


def check_session_access(db: Session, user: User, session: AttendanceSession) -> None:
	if session.class_id is None:
		if not is_admin(user):
			raise HTTPException(status_code=403, detail="Only administrators can access general sessions")
		return
	require_class_access(db, user, session.class_id)


@router.get("", response_model=list[AttendanceSessionResponse])
def list_sessions(
	session_date: date | None = None,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> list[AttendanceSession]:
	return list_accessible_sessions(db, current_user, session_date)


@router.post("", response_model=AttendanceSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
	session_data: AttendanceSessionCreate,
	db: Session = Depends(get_db),
	current_user: User = Depends(session_manager),
) -> AttendanceSession:
	if session_data.end_time <= session_data.start_time:
		raise HTTPException(status_code=422, detail="Session end time must be after start time")
	if session_data.session_type == SessionType.CLASS and session_data.class_id is None:
		raise HTTPException(status_code=422, detail="Class sessions require a class")
	if session_data.session_type == SessionType.GENERAL and session_data.class_id is not None:
		raise HTTPException(status_code=422, detail="General sessions cannot be assigned to a class")
	if session_data.session_type == SessionType.GENERAL and not is_admin(current_user):
		raise HTTPException(status_code=403, detail="Only administrators can create general sessions")
	if session_data.class_id is not None:
		class_exists = db.get(Class, session_data.class_id)
		if class_exists is None:
			raise HTTPException(status_code=404, detail="Class not found")
		require_class_access(db, current_user, session_data.class_id)
	session = AttendanceSession(**session_data.model_dump(), created_by=current_user.id)
	db.add(session)
	try:
		db.flush()
		record_audit(db, current_user, "CREATE", "session", session.id, f"Created attendance session {session.name}")
		db.commit()
	except IntegrityError as error:
		db.rollback()
		raise HTTPException(status_code=409, detail="A session with that name already exists on this date") from error
	db.refresh(session)
	return session


@router.patch("/{session_id}", response_model=AttendanceSessionResponse)
def update_session(
	session_id: int,
	session_data: AttendanceSessionUpdate,
	db: Session = Depends(get_db),
	current_user: User = Depends(session_manager),
) -> AttendanceSession:
	session = get_session(db, session_id)
	check_session_access(db, current_user, session)
	if not is_admin(current_user) and session.created_by != current_user.id:
		raise HTTPException(status_code=403, detail="Only the session creator or an administrator can update it")
	changes = session_data.model_dump(exclude_unset=True)
	session_type = changes.get("session_type", session.session_type)
	class_id = changes.get("class_id", session.class_id)
	if session_type == SessionType.GENERAL:
		if not is_admin(current_user):
			raise HTTPException(status_code=403, detail="Only administrators can manage general sessions")
		if class_id is not None:
			raise HTTPException(status_code=422, detail="General sessions cannot be assigned to a class")
	elif class_id is None:
		raise HTTPException(status_code=422, detail="Class sessions require a class")
	start_time = changes.get("start_time", session.start_time)
	end_time = changes.get("end_time", session.end_time)
	if end_time <= start_time:
		raise HTTPException(status_code=422, detail="Session end time must be after start time")
	if class_id is not None:
		class_exists = db.get(Class, class_id)
		if class_exists is None:
			raise HTTPException(status_code=404, detail="Class not found")
		require_class_access(db, current_user, class_id)
	old_values = {key: getattr(session, key).value if hasattr(getattr(session, key), "value") else str(getattr(session, key)) for key in changes}
	for key, value in changes.items():
		setattr(session, key, value)
	record_audit(db, current_user, "UPDATE", "session", session.id, f"Updated session {session.name}", old_values=old_values)
	db.commit()
	db.refresh(session)
	return session


@router.post("/{session_id}/open", response_model=AttendanceSessionResponse)
def open_session(
	session_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(session_manager),
) -> AttendanceSession:
	session = get_session(db, session_id)
	check_session_access(db, current_user, session)
	if session.status not in {SessionStatus.SCHEDULED, SessionStatus.CLOSED}:
		raise HTTPException(status_code=409, detail="Only scheduled or closed sessions can be opened")
	session.status = SessionStatus.OPEN
	record_audit(db, current_user, "OPEN", "session", session.id, f"Opened session {session.name}")
	db.commit()
	db.refresh(session)
	return session


@router.post("/{session_id}/close", response_model=AttendanceSessionResponse)
def close_session(
	session_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(session_manager),
) -> AttendanceSession:
	session = get_session(db, session_id)
	check_session_access(db, current_user, session)
	if session.status != SessionStatus.OPEN:
		raise HTTPException(status_code=409, detail="Only open sessions can be closed")
	session.status = SessionStatus.CLOSED
	record_audit(db, current_user, "CLOSE", "session", session.id, f"Closed session {session.name}")
	db.commit()
	db.refresh(session)
	return session
