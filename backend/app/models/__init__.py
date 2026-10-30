"""模型包。导入本包即完成全部表结构注册。"""

from app.db.base import Base
from app.models.catalog import ClassSession, Course, ScheduleUser
from app.models.enums import (
    EMOTION_LABELS,
    Emotion,
    Role,
    SessionStatus,
    Source,
    UserStatus,
    compute_session_status,
    emotion_label,
)
from app.models.record import AuditLog, EmojiRecord
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Course",
    "ClassSession",
    "ScheduleUser",
    "EmojiRecord",
    "AuditLog",
    "Role",
    "UserStatus",
    "Source",
    "Emotion",
    "SessionStatus",
    "EMOTION_LABELS",
    "emotion_label",
    "compute_session_status",
]
