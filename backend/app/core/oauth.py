from datetime import datetime, timedelta, timezone

from authlib.integrations.starlette_client import OAuth
import jwt
from jwt import InvalidTokenError

from app.core.config import settings
from app.security.jwt import ALGORITHM


oauth = OAuth()

if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

if settings.APPLE_CLIENT_ID and settings.APPLE_CLIENT_SECRET:
    oauth.register(
        name="apple",
        client_id=settings.APPLE_CLIENT_ID,
        client_secret=settings.APPLE_CLIENT_SECRET,
        server_metadata_url="https://appleid.apple.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email name"},
    )


def create_signup_handoff_token(
    provider: str,
    subject: str,
    email: str,
    first_name: str,
    last_name: str,
) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "purpose": "oauth_student_signup",
            "provider": provider,
            "provider_sub": subject,
            "email": email,
            "email_verified": True,
            "first_name": first_name,
            "last_name": last_name,
            "iat": now,
            "exp": now + timedelta(minutes=10),
        },
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def read_signup_handoff_token(token: str) -> dict:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    if (
        payload.get("purpose") != "oauth_student_signup"
        or payload.get("provider") not in {"google", "apple"}
        or not payload.get("provider_sub")
        or not payload.get("email_verified")
        or not payload.get("email")
    ):
        raise InvalidTokenError("Invalid OAuth signup handoff")
    return payload