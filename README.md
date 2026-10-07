# Empower Hope Attendance

A role-based attendance system for the Empower Hope learning community. The MVP includes administrator, staff, and student accounts; class enrollment and staff assignments; scheduled attendance sessions; present, absent, late, and excused records; dashboards; CSV reports; and an audit trail.

## Run with Docker

Requirements: Docker Desktop with Docker Compose.

1. From the repository root, start the application:

	```sh
	cp .env.example .env
	python -c "import secrets; print(secrets.token_urlsafe(48))"
	# Put a generated value in SECRET_KEY; set a unique POSTGRES_PASSWORD too.
	docker compose up --build
	```

2. Open [http://localhost:8000](http://localhost:8000). The backend container applies database migrations before starting the API.

3. In another terminal, create the first Super Admin. The script prompts for the name, email, and password:

	```sh
	docker compose exec backend python -m scripts.create_admin
	```

4. Sign in at `http://localhost:8000` using the Super Admin's **email address** and password. The sign-in field is labeled Student ID, but it also accepts admin email addresses.

5. To create a separate Admin account, open **People** → **Add a person**, fill in the account details, and select **Administrator**. Sign out, then sign in using that Admin's email address and temporary password. The bootstrap script creates a Super Admin; use the People page to create additional administrators.

The Compose file requires `POSTGRES_PASSWORD` and `SECRET_KEY`; it has no built-in default credentials. The database is persisted in the `postgres_data` volume. For hosted deployments, use a dedicated least-privilege database account and TLS for any database connection that crosses a machine or network boundary.

### Google and Apple Sign-In

Docker Compose reads provider settings from a root `.env` file (not `backend/.env`). Copy the root `.env.example` to `.env`, then set `PUBLIC_BASE_URL` and credentials for the provider(s) you want to enable. When running Uvicorn directly from `backend`, configure the same values in `backend/.env`.

For local Google testing, set `PUBLIC_BASE_URL=http://localhost:8000` in the root `.env` and add this exact callback URI to a Google OAuth client configured as a Web application:

- `http://localhost:8000/api/v1/auth/oauth/google/callback`

For production, set `PUBLIC_BASE_URL` to the app's public HTTPS origin and register the corresponding callback URI with each provider:

- Google: `https://your-domain.example/api/v1/auth/oauth/google/callback`
- Apple: `https://your-domain.example/api/v1/auth/oauth/apple/callback`

Apple requires HTTPS and a Sign in with Apple Services ID associated with the app's primary App ID. Configure the Services ID's return URL to the Apple callback above, and generate the Apple client-secret JWT using the Apple team, key, and Services ID. Keep all provider secrets server-side. After provider verification, new students choose their Student ID and class and set a password; verified existing student accounts can sign in directly. Local HTTP testing is suitable for Google only; use an HTTPS deployment or tunnel for Apple.

## Run Locally

The backend expects PostgreSQL. Copy `backend/.env.example` to `backend/.env`, set a unique `SECRET_KEY` of at least 32 characters and the database URL, then from `backend` run:

```sh
python -m venv ../.venv
../.venv/Scripts/python.exe -m pip install -r requirements.txt
../.venv/Scripts/python.exe -m alembic upgrade head
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

On macOS/Linux, activate the virtual environment and use `python` for the commands above. The browser app and API are served from the same origin; API documentation is at `/docs` and liveness is at `/health`.

## Workflows

- **Administrators:** manage users, classes, enrollments, staff assignments, sessions, reports, and audit history.
- **Staff:** view assigned classes, create sessions for assigned classes, open/close sessions, and record attendance.
- **Students:** view their schedule, dashboard summary, and attendance history.
- Attendance records are unique per session and student. Marking requires an open session; an administrator can correct a record after the session closes.
- Passwords are hashed with Argon2id through `pwdlib`; API access uses signed JWT bearer tokens.

## Project Layout

- `backend/app`: FastAPI routes, SQLAlchemy models, security, and services
- `backend/migrations`: Alembic database migrations
- `frontend`: static HTML, CSS, and JavaScript application served by FastAPI
- `docker-compose.yml`: local PostgreSQL and app services

## Configuration

See `backend/.env.example` for supported settings. Keep `.env` files and production credentials out of version control. `API_PREFIX` defaults to `/api/v1`.

Login attempts are limited to 10 per account and 100 per source IP in a 15-minute window. The limiter is in-process; deployments with multiple workers or replicas should enforce the same limits at a shared gateway or distributed limiter. The app adds browser security headers and a restrictive content-security policy to the main UI. Never use example credentials in a deployment. If a credential has entered Git history, rotate it; deleting the current file does not remove old history.

## Current MVP Boundaries

This is a single-organization attendance app. It does not yet provide password reset/email delivery, multi-tenant isolation, self-service registration, or automated deployment. Review secrets, HTTPS, backups, and operational monitoring before exposing it to the public internet.
