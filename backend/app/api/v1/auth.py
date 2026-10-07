from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from starlette.requests import Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from jwt import InvalidTokenError

from app.core.dependencies import get_current_user
from app.core.rate_limit import login_rate_limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.core.config import settings
from app.core.oauth import create_signup_handoff_token, oauth, read_signup_handoff_token
from app.database.session import get_db
from app.models.class_model import Class
from app.models.enrollment import Enrollment
from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.repositories.user_repository import get_by_email, get_by_student_id
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    OAuthRegisterRequest,
    PasswordChangeRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services.auth_service import authenticate_user
from app.services.audit_service import record_audit


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


def _create_student_account(
    db: Session,
    *,
    email: str,
    student_id: str,
    first_name: str,
    last_name: str,
    class_name: str,
    password_hash: str,
    oauth_provider: str | None = None,
    oauth_subject: str | None = None,
) -> User:
    if get_by_email(db, email) is not None:
        raise HTTPException(status_code=409, detail="Email is already registered")
    if get_by_student_id(db, student_id) is not None:
        raise HTTPException(status_code=409, detail="Student ID is already registered")

    class_ = db.scalar(select(Class).where(Class.name == class_name))
    if class_ is None:
        class_ = Class(name=class_name)
        db.add(class_)
        db.flush()

    user = User(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=email,
        student_id=student_id,
        password_hash=password_hash,
        role=UserRole.STUDENT,
        status=UserStatus.ACTIVE,
        is_active=True,
    )
    if oauth_provider and oauth_subject:
        setattr(user, f"{oauth_provider}_subject", oauth_subject)
    db.add(user)
    try:
        db.flush()
        db.add(Enrollment(student_id=user.id, class_id=class_.id))
        record_audit(db, None, "REGISTER", "user", user.id, f"Created student account {user.student_id}")
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or student ID is already registered",
        ) from error
    db.refresh(user)
    return user


def _oauth_frontend_redirect(**fragment_values: str) -> RedirectResponse:
    base_url = settings.PUBLIC_BASE_URL.rstrip("/")
    return RedirectResponse(f"{base_url}/#{urlencode(fragment_values)}", status_code=303)


def _oauth_callback_url(provider: str) -> str:
    base_url = settings.PUBLIC_BASE_URL.rstrip("/")
    return f"{base_url}{settings.API_PREFIX}/auth/oauth/{provider}/callback"


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
    request: Request = None,
) -> TokenResponse:
    client_ip = request.client.host if request is not None and request.client else "unknown"
    login_rate_limiter.check_and_consume(client_ip, login_data.identifier)
    user = authenticate_user(db, login_data.identifier, login_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid sign-in ID or email, or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token = create_access_token(
        user_id=str(user.id),
        role=user.role.value,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    register_data: RegisterRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    email = str(register_data.email).lower()
    student_id = register_data.student_id.strip().upper()
    user = _create_student_account(
        db,
        email=email,
        student_id=student_id,
        first_name=register_data.first_name,
        last_name=register_data.last_name,
        class_name=register_data.class_name,
        password_hash=hash_password(register_data.password),
    )

    return TokenResponse(
        access_token=create_access_token(user_id=str(user.id), role=user.role.value),
        token_type="bearer",
    )


@router.get("/oauth/{provider}/start", include_in_schema=False)
async def start_oauth(provider: str, request: Request) -> RedirectResponse:
    if provider not in {"google", "apple"}:
        return _oauth_frontend_redirect(oauth_error="unsupported_provider")
    client = oauth.create_client(provider)
    if client is None:
        return _oauth_frontend_redirect(oauth_error=f"{provider}_not_configured")
    options = {"response_mode": "form_post"} if provider == "apple" and settings.PUBLIC_BASE_URL.startswith("https://") else {}
    return await client.authorize_redirect(request, _oauth_callback_url(provider), **options)


@router.post("/oauth/{provider}/callback", include_in_schema=False)
@router.get("/oauth/{provider}/callback", include_in_schema=False)
async def oauth_callback(provider: str, request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    if provider not in {"google", "apple"}:
        return _oauth_frontend_redirect(oauth_error="unsupported_provider")
    client = oauth.create_client(provider)
    if client is None:
        return _oauth_frontend_redirect(oauth_error=f"{provider}_not_configured")

    try:
        token = await client.authorize_access_token(request)
        identity = token.get("userinfo") or {}
    except Exception:
        return _oauth_frontend_redirect(oauth_error=f"{provider}_verification_failed")

    email = str(identity.get("email") or "").strip().lower()
    verified = str(identity.get("email_verified", "")).lower() == "true"
    subject = str(identity.get("sub") or "")
    if not email or not verified or not subject:
        return _oauth_frontend_redirect(oauth_error="verified_email_required")

    subject_field = f"{provider}_subject"
    existing_user = db.scalar(select(User).where(getattr(User, subject_field) == subject))
    if existing_user is not None:
        if existing_user.role != UserRole.STUDENT or not existing_user.is_active:
            return _oauth_frontend_redirect(oauth_error="student_account_required")
        access_token = create_access_token(user_id=str(existing_user.id), role=existing_user.role.value)
        return _oauth_frontend_redirect(oauth_access_token=access_token)

    existing_user = get_by_email(db, email)
    if existing_user is not None:
        if existing_user.role != UserRole.STUDENT or not existing_user.is_active:
            return _oauth_frontend_redirect(oauth_error="student_account_required")
        try:
            setattr(existing_user, subject_field, subject)
            db.commit()
        except IntegrityError:
            db.rollback()
            return _oauth_frontend_redirect(oauth_error=f"{provider}_account_link_failed")
        access_token = create_access_token(user_id=str(existing_user.id), role=existing_user.role.value)
        return _oauth_frontend_redirect(oauth_access_token=access_token)

    full_name = str(identity.get("name") or "").strip().split(maxsplit=1)
    first_name = str(identity.get("given_name") or (full_name[0] if full_name else ""))
    last_name = str(identity.get("family_name") or (full_name[1] if len(full_name) > 1 else ""))
    handoff_token = create_signup_handoff_token(provider, subject, email, first_name, last_name)
    return _oauth_frontend_redirect(
        oauth_signup_token=handoff_token,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )


@router.post("/register/oauth", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_with_oauth(
    signup_data: OAuthRegisterRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        identity = read_signup_handoff_token(signup_data.oauth_token)
    except InvalidTokenError as error:
        raise HTTPException(status_code=400, detail="OAuth signup has expired. Please start again.") from error

    email = str(identity["email"]).lower()
    provider = str(identity["provider"])
    subject = str(identity["provider_sub"])
    subject_field = f"{provider}_subject"
    if db.scalar(select(User.id).where(getattr(User, subject_field) == subject)) is not None:
        raise HTTPException(status_code=409, detail="OAuth signup was already completed. Sign in instead.")

    existing_user = get_by_email(db, email)
    if existing_user is not None:
        if existing_user.role != UserRole.STUDENT or not existing_user.is_active:
            raise HTTPException(status_code=409, detail="This email is already linked to a non-student account")
        user = existing_user
    else:
        first_name = str(identity.get("first_name") or signup_data.first_name)
        last_name = str(identity.get("last_name") or signup_data.last_name)
        user = _create_student_account(
            db,
            email=email,
            student_id=signup_data.student_id.strip().upper(),
            first_name=first_name,
            last_name=last_name,
            class_name=signup_data.class_name,
            password_hash=hash_password(signup_data.password),
            oauth_provider=provider,
            oauth_subject=subject,
        )

    return TokenResponse(
        access_token=create_access_token(user_id=str(user.id), role=user.role.value),
        token_type="bearer",
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> CurrentUserResponse:

    return CurrentUserResponse.model_validate(current_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    current_user.password_hash = hash_password(password_data.new_password)
    record_audit(db, current_user, "CHANGE_PASSWORD", "user", current_user.id, "Changed account password")
    db.commit()