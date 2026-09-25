from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import AssignmentStatus


class ClassStaff(Base):
    __tablename__ = "class_staff"

    __table_args__ = (
        UniqueConstraint(
            "class_id",
            "staff_id",
            name="uq_class_staff",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    class_id: Mapped[int] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"),
        nullable=False,
    )

    staff_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus, name="assignment_status"),
        nullable=False,
        default=AssignmentStatus.ACTIVE,
    )

    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    class_ = relationship(
        "Class",
        back_populates="staff_assignments",
    )

    staff = relationship(
        "User",
        back_populates="class_assignments",
    )