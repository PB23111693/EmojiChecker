"""领域枚举。与设计方案 8.2 的七类表情保持一致。"""

from __future__ import annotations

import datetime as dt
from enum import StrEnum


class Role(StrEnum):
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    ADMIN = "ADMIN"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class Source(StrEnum):
    MANUAL = "MANUAL"
    AI = "AI"


class Emotion(StrEnum):
    HAPPY = "HAPPY"
    NEUTRAL = "NEUTRAL"
    SAD = "SAD"
    ANGRY = "ANGRY"
    SURPRISED = "SURPRISED"
    FEARFUL = "FEARFUL"
    DISGUST = "DISGUST"


class SessionStatus(StrEnum):
    PENDING = "PENDING"
    ONGOING = "ONGOING"
    ENDED = "ENDED"
    CANCELLED = "CANCELLED"


EMOTION_LABELS: dict[Emotion, tuple[str, str]] = {
    Emotion.HAPPY: ("开心", "😄"),
    Emotion.NEUTRAL: ("平静", "😐"),
    Emotion.SAD: ("低落", "😢"),
    Emotion.ANGRY: ("生气", "😠"),
    Emotion.SURPRISED: ("惊讶", "😮"),
    Emotion.FEARFUL: ("害怕", "😨"),
    Emotion.DISGUST: ("厌恶", "🤢"),
}


def emotion_label(value: Emotion) -> str:
    label, symbol = EMOTION_LABELS[value]
    return f"{symbol} {label}"


def compute_session_status(
    start_at: dt.datetime,
    end_at: dt.datetime,
    cancelled: bool,
    now: dt.datetime | None = None,
) -> SessionStatus:
    """课堂状态由服务器时间推导，区间为左闭右开 [start_at, end_at)。"""
    if cancelled:
        return SessionStatus.CANCELLED
    current = now or dt.datetime.now(dt.timezone.utc)
    if current < start_at:
        return SessionStatus.PENDING
    if current < end_at:
        return SessionStatus.ONGOING
    return SessionStatus.ENDED
