from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.router import api_router
from app.core.config import settings


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)


app.include_router(api_router, prefix=settings.API_PREFIX)
is_https = settings.PUBLIC_BASE_URL.lower().startswith("https://")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=600,
    same_site="none" if is_https else "lax",
    https_only=is_https,
)

@app.middleware("http")
async def security_headers(request: Request, call_next):
	response = await call_next(request)
	response.headers["X-Content-Type-Options"] = "nosniff"
	response.headers["X-Frame-Options"] = "DENY"
	response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
	response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
	response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
	if request.url.path in {"/", "/index.html"}:
		response.headers["Content-Security-Policy"] = (
			"default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
			"form-action 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; "
			"font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https://empowerhope.org; "
			"connect-src 'self'"
		)
	if is_https:
		response.headers["Strict-Transport-Security"] = "max-age=31536000"
	return response


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "database": "configured",
    }


@app.get("/login.html", include_in_schema=False)
def legacy_login_page() -> RedirectResponse:
    return RedirectResponse(url="/", status_code=307)


@app.get("/dashboard.html", include_in_schema=False)
def legacy_dashboard_page() -> RedirectResponse:
    return RedirectResponse(url="/?view=overview", status_code=307)


@app.get("/pages/{role}/{page}.html", include_in_schema=False)
def legacy_role_page(role: str, page: str) -> RedirectResponse:
    view_by_page = {
        "dashboard": "overview",
        "attendance": "reports" if role == "student" else "attendance",
        "classes": "classes",
        "sessions": "sessions",
        "reports": "reports",
        "users": "people",
        "audit-logs": "audit",
        "profile": "profile",
    }
    return RedirectResponse(url=f"/?view={view_by_page.get(page, 'overview')}", status_code=307)


frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")