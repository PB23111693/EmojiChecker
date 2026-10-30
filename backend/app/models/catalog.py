"""课程、课堂与课堂名单。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntType, UTCDateTime, utcnow
from app.models.user import User


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    teacher_id: Mapped[int] = mapped_column(
        BigIntType, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    teacher: Mapped[User] = relationship(back_populates="courses", lazy="joined")
    sessions: Mapped[list["ClassSession"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("name", "teacher_id", name="uq_course_name_teacher"),)


class ClassSession(Base):
    __tablename__ = "class_sessions"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        BigIntType, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    class_name: Mapped[str] = mapped_column(String(60), nullable=False)
    room: Mapped[str | None] = mapped_column(String(60), nullable=True)
    start_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, nullable=False)
    end_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, nullable=False)
    cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.6)
    created_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    course: Mapped[Course] = relationship(back_populates="sessions", lazy="joined")
    members: Mapped[list["ScheduleUser"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_session_course_start", "course_id", "start_at"),
        Index("ix_session_start_end", "start_at", "end_at"),
    )


class ScheduleUser(Base):
    __tablename__ = "schedule_users"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigIntType, ForeignKey("class_sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigIntType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    arranged_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    session: Mapped[ClassSession] = relationship(back_populates="members")
    user: Mapped[User] = relationship(lazy="joined")

    __table_args__ = (UniqueConstraint("session_id", "user_id", name="uq_schedule_session_user"),)
