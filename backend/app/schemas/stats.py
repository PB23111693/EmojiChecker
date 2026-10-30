"""统计与看板数据结构。"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field

from app.models.enums import Emotion, Source


class EmotionCount(BaseModel):
    emotion: Emotion
    count: int
    ratio: float


class TrendPoint(BaseModel):
    bucket: str
    manual: int = 0
    ai: int = 0


class ManualBlock(BaseModel):
    total: int = 0
    participants: int = 0
    member_count: int = 0
    coverage: float | None = None
    distribution: list[EmotionCount] = Field(default_factory=list)


class AiBlock(BaseModel):
    total: int = 0
    threshold: float = 0.6
    last_observed_at: dt.datetime | None = None
    distribution: list[EmotionCount] = Field(default_factory=list)


class DashboardOut(BaseModel):
    session_id: int
    course_name: str
    class_name: str
    status: str
    manual: ManualBlock
    ai: AiBlock
    trend: list[TrendPoint] = Field(default_factory=list)
    last_update_at: dt.datetime


class StatisticsOut(BaseModel):
    total: int
    manual_total: int
    ai_total: int
    participants: int
    distribution: list[EmotionCount]
    by_source: dict[str, int]
    trend: list[TrendPoint]
    filters: dict[str, str | None] = Field(default_factory=dict)


class ClassOption(BaseModel):
    class_name: str
    session_count: int
