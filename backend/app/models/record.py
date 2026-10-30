"""表情记录与审计日志。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntType, UTCDateTime, utcnow
from app.models.catalog import ClassSession
from app.models.enums import Emotion, Source
from app.models.user import User, enum_type


class EmojiRecord(Base):
    __tablename__ = "emoji_records"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    session_id: Mapped[int] = mapped_column(
        BigIntType, ForeignKey("class_sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        BigIntType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    emotion: Mapped[Emotion] = mapped_column(
        enum_type(Emotion, "emotion_enum"), nullable=False
    )
    source: Mapped[Source] = mapped_column(enum_type(Source, "source_enum"), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(60), nullable=True)
    observed_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, nullable=False)
    received_at: Mapped[dt.datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    manual_slot: Mapped[int | None] = mapped_column(BigIntType, nullable=True)

    session: Mapped[ClassSession] = relationship(lazy="joined")
    user: Mapped[User | None] = relationship(lazy="joined")

    __table_args__ = (
        # 同一学生、同一课堂、同一时间片只允许一条手动记录。
        # MySQL 与 SQLite 的唯一索引都允许多个 NULL，因此不影响匿名 AI 记录。
        UniqueConstraint("user_id", "session_id", "manual_slot", name="uq_emoji_manual_slot"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_emoji_confidence_range",
        ),
        CheckConstraint(
            "source != 'MANUAL' OR (user_id IS NOT NULL "
            "AND confidence IS NULL AND device_id IS NULL)",
            name="ck_emoji_manual_shape",
        ),
        CheckConstraint(
            "source != 'AI' OR (user_id IS NULL AND manual_slot IS NULL "
            "AND confidence IS NOT NULL AND device_id IS NOT NULL)",
            name="ck_emoji_ai_shape",
        ),
        Index("ix_emoji_session_observed", "session_id", "observed_at"),
        Index("ix_emoji_user_observed", "user_id", "observed_at"),
        Index("ix_emoji_source_observed", "source", "observed_at"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    actor_id: Mapped[int | None] = mapped_column(
        BigIntType, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    result: Mapped[str] = mapped_column(String(20), nullable=False, default="SUCCESS")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utcnow, index=True
    )

    __table_args__ = (
        CheckConstraint(
            "result IN ('SUCCESS', 'FAILURE')", name="ck_audit_result"
        ),
    )
