from datetime import date, datetime, time

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import SessionStatus, SessionType


class AttendanceSession(Base):
    __tablename__ = "sessions"

    __table_args__ = (
        UniqueConstraint(
            "session_date",
            "name",
            name="uq_session_date_name",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    session_type: Mapped[SessionType] = mapped_column(
        Enum(SessionType, name="session_type"),
        nullable=False,
    )

    session_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status"),
        nullable=False,
        default=SessionStatus.SCHEDULED,
    )

    class_id: Mapped[int | None] = mapped_column(
        ForeignKey("classes.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    class_ = relationship(
        "Class",
        back_populates="sessions",
    )

    created_by_user = relationship(
        "User",
        back_populates="created_sessions",
    )

    attendance_records = relationship(
        "Attendance",
        back_populates="session",
        cascade="all, delete-orphan",
    )