from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.attendance import Attendance
from app.models.enums import AttendanceStatus, SessionStatus, UserRole
from app.models.session import AttendanceSession
from app.models.user import User
from app.permissions.access_control import is_admin, require_class_access
from app.schemas.attendance import AttendanceBulkMark, AttendanceMark, AttendanceResponse, RosterEntry
from app.core.dependencies import get_current_user, require_roles
from app.repositories.attendance_repository import get_by_id, list_for_session
from app.services.audit_service import record_audit
from app.services.attendance_service import eligible_students


router = APIRouter(prefix="/attendance", tags=["Attendance"])
attendance_staff = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.STAFF)


def get_session(db: Session, session_id: int) -> AttendanceSession:
	session = db.get(AttendanceSession, session_id)
	if session is None:
		raise HTTPException(status_code=404, detail="Attendance session not found")
	return session


def check_access(db: Session, current_user: User, session: AttendanceSession) -> None:
	if session.class_id is None:
		if not is_admin(current_user):
			raise HTTPException(status_code=403, detail="Only administrators can access general sessions")
		return
	require_class_access(db, current_user, session.class_id)


def get_session_students(db: Session, session: AttendanceSession) -> list[User]:
	return eligible_students(db, session)


@router.get("/sessions/{session_id}/roster", response_model=list[RosterEntry])
def get_roster(
	session_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(attendance_staff),
) -> list[dict]:
	session = get_session(db, session_id)
	check_access(db, current_user, session)
	students = get_session_students(db, session)
	attendance_records = {
		record.student_id: record
		for record in list_for_session(db, session.id)
	}
	return [
		{
			"student_id": student.id,
			"first_name": student.first_name,
			"last_name": student.last_name,
			"email": student.email,
			"attendance_id": attendance_records[student.id].id if student.id in attendance_records else None,
			"status": attendance_records[student.id].status if student.id in attendance_records else None,
			"notes": attendance_records[student.id].notes if student.id in attendance_records else None,
		}
		for student in students
	]


@router.post("/sessions/{session_id}/mark", response_model=list[AttendanceResponse])
def mark_roster(
	session_id: int,
	data: AttendanceBulkMark,
	db: Session = Depends(get_db),
	current_user: User = Depends(attendance_staff),
) -> list[Attendance]:
	session = get_session(db, session_id)
	check_access(db, current_user, session)
	if session.status != SessionStatus.OPEN:
		raise HTTPException(status_code=409, detail="Attendance can only be marked while the session is open")
	entries = {entry.student_id: entry for entry in data.records}
	if len(entries) != len(data.records):
		raise HTTPException(status_code=422, detail="A student may only appear once per submission")
	eligible_ids = {student.id for student in get_session_students(db, session)}
	invalid_ids = set(entries) - eligible_ids
	if invalid_ids:
		raise HTTPException(status_code=422, detail="Every student must be actively enrolled in this session")

	existing_records = {
		record.student_id: record
		for record in db.scalars(
			select(Attendance).where(
				Attendance.session_id == session.id,
				Attendance.student_id.in_(entries),
			)
		).all()
	}
	now = datetime.now(timezone.utc)
	records = []
	for student_id, entry in entries.items():
		record = existing_records.get(student_id)
		old_status = record.status.value if record is not None else None
		if record is None:
			record = Attendance(session_id=session.id, student_id=student_id)
			db.add(record)
		record.status = entry.status
		record.notes = entry.notes
		record.marked_by = current_user.id
		record.sign_in_at = now if entry.status in {AttendanceStatus.PRESENT, AttendanceStatus.LATE} else None
		records.append(record)
	db.flush()
	for record, entry in zip(records, entries.values()):
		record_audit(
			db,
			current_user,
			"MARK_ATTENDANCE",
			"attendance",
			record.id,
			f"Marked student {student_id} {entry.status.value.lower()} for {session.name}",
			old_values={"status": old_status},
			new_values={"status": entry.status.value, "notes": entry.notes},
		)
	try:
		db.commit()
	except IntegrityError as error:
		db.rollback()
		raise HTTPException(status_code=409, detail="Attendance changed concurrently; reload the roster") from error
	for record in records:
		db.refresh(record)
	return records


@router.get("/sessions/{session_id}", response_model=list[AttendanceResponse])
def list_session_attendance(
	session_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> list[Attendance]:
	session = get_session(db, session_id)
	if current_user.role == UserRole.STUDENT:
		return list(db.scalars(select(Attendance).where(
			Attendance.session_id == session_id,
			Attendance.student_id == current_user.id,
		)).all())
	check_access(db, current_user, session)
	return list(db.scalars(select(Attendance).where(Attendance.session_id == session_id).order_by(Attendance.student_id)).all())


@router.patch("/{attendance_id}", response_model=AttendanceResponse)
def update_attendance(
	attendance_id: int,
	data: AttendanceMark,
	db: Session = Depends(get_db),
	current_user: User = Depends(attendance_staff),
) -> Attendance:
	record = get_by_id(db, attendance_id)
	if record is None:
		raise HTTPException(status_code=404, detail="Attendance record not found")
	session = get_session(db, record.session_id)
	check_access(db, current_user, session)
	if session.status != SessionStatus.OPEN and not is_admin(current_user):
		raise HTTPException(status_code=409, detail="Only administrators can correct attendance after a session closes")
	old_status = record.status.value
	record.status = data.status
	record.notes = data.notes
	record.marked_by = current_user.id
	record.sign_in_at = datetime.now(timezone.utc) if data.status in {AttendanceStatus.PRESENT, AttendanceStatus.LATE} else None
	record_audit(
		db,
		current_user,
		"CORRECT_ATTENDANCE",
		"attendance",
		record.id,
		"Corrected attendance record",
		old_values={"status": old_status},
		new_values={"status": data.status.value, "notes": data.notes},
	)
	db.commit()
	db.refresh(record)
	return record
