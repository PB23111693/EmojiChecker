"""AI 服务接口数据结构。"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field

from app.models.enums import Emotion


class AiContextOut(BaseModel):
    session_id: int
    course_name: str
    class_name: str
    start_at: dt.datetime
    end_at: dt.datetime
    status: str
    ai_threshold: float
    sample_interval_seconds: int = 3
    max_faces_per_frame: int = 5
    emotions: list[str] = Field(default_factory=list)


class AiResultItem(BaseModel):
    event_id: str = Field(min_length=8, max_length=36)
    observed_at: dt.datetime
    emotion: Emotion
    confidence: float = Field(ge=0, le=1)


class AiBatchRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=60)
    session_id: int = Field(gt=0)
    model_version: str = Field(min_length=1, max_length=60)
    results: list[AiResultItem] = Field(min_length=1, max_length=100)


class AiEventResult(BaseModel):
    event_id: str
    status: str
    reason: str | None = None
    record_id: int | None = None


class AiBatchResponse(BaseModel):
    accepted: int = 0
    duplicates: int = 0
    rejected: int = 0
    details: list[AiEventResult] = Field(default_factory=list)
