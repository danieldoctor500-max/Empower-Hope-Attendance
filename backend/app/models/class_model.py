from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import ClassStatus


class Class(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[ClassStatus] = mapped_column(
        Enum(ClassStatus, name="class_status"),
        nullable=False,
        default=ClassStatus.ACTIVE,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    enrollments = relationship(
        "Enrollment",
        back_populates="class_",
        cascade="all, delete-orphan",
    )

    staff_assignments = relationship(
        "ClassStaff",
        back_populates="class_",
        cascade="all, delete-orphan",
    )

    sessions = relationship(
        "AttendanceSession",
        back_populates="class_",
    )