"""表情记录数据结构。"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field

from app.models.enums import Emotion, Source


class EmojiSubmitRequest(BaseModel):
    event_id: str = Field(min_length=8, max_length=36)
    session_id: int = Field(gt=0)
    emotion: Emotion


class EmojiSubmitResult(BaseModel):
    record_id: int
    observed_at: dt.datetime
    duplicate: bool = False


class EmojiRecordOut(BaseModel):
    id: int
    event_id: str
    session_id: int
    course_name: str
    class_name: str
    user_id: int | None = None
    username: str | None = None
    emotion: Emotion
    source: Source
    confidence: float | None = None
    device_id: str | None = None
    observed_at: dt.datetime
    received_at: dt.datetime
