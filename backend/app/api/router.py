from fastapi import APIRouter

from app.api.v1.attendance import router as attendance_router
from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.auth import router as auth_router
from app.api.v1.classes import router as classes_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.enrollments import router as enrollments_router
from app.api.v1.reports import router as reports_router
from app.api.v1.sessions import router as sessions_router
from app.api.v1.users import router as users_router


api_router = APIRouter()
for router in (
	auth_router,
	users_router,
	classes_router,
	enrollments_router,
	sessions_router,
	attendance_router,
	dashboard_router,
	reports_router,
	audit_logs_router,
):
	api_router.include_router(router)
