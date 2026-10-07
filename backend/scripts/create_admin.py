from getpass import getpass

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.security.password import hash_password


def create_admin() -> None:
    first_name = input("First name: ").strip()
    last_name = input("Last name: ").strip()
    email = input("Email: ").strip().lower()

    password = getpass("Password: ")
    confirm_password = getpass("Confirm password: ")

    if password != confirm_password:
        print("Error: passwords do not match.")
        return

    if len(password) < 12:
        print("Error: password must be at least 12 characters.")
        return

    db = SessionLocal()

    try:
        existing_user = db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

        if existing_user:
            print(f"Error: user with email {email} already exists.")
            return

        admin = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            is_active=True,
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print()
        print("SUPER_ADMIN created successfully.")
        print(f"User ID: {admin.id}")
        print(f"Email: {admin.email}")
        print(f"Role: {admin.role.value}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    create_admin()