from app.models.enums import UserRole

ADMIN_ROLES = frozenset({UserRole.ADMIN, UserRole.SUPER_ADMIN})
STAFF_ROLES = frozenset({UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.STAFF})
ALL_ROLES = frozenset(UserRole)
