from getpass import getpass

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.enums import UserRole
from app.models.user import User
from app.security.password import hash_password


def reset_admin_password() -> None:
    email = input("Super Admin email: ").strip().lower()
    password = getpass("New password: ")
    confirm_password = getpass("Confirm new password: ")

    if password != confirm_password:
        print("Error: passwords do not match.")
        return

    if len(password) < 12:
        print("Error: password must be at least 12 characters.")
        return

    if len(password) > 128:
        print("Error: password must be no more than 128 characters.")
        return

    db = SessionLocal()

    try:
        admin = db.execute(
            select(User).where(
                User.email == email,
                User.role == UserRole.SUPER_ADMIN,
            )
        ).scalar_one_or_none()

        if admin is None:
            print("Error: no Super Admin account found with that email.")
            return

        admin.password_hash = hash_password(password)
        db.commit()
        print("Super Admin password reset successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reset_admin_password()
