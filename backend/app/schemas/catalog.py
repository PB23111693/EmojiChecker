"""课程、课堂与名单数据结构。"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.text import normalize_class_name
from app.models.enums import SessionStatus


class CourseCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    teacher_id: int = Field(gt=0)

    @field_validator("name")
    @classmethod
    def _strip(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("课程名称不能为空")
        return cleaned


class CourseOut(BaseModel):
    id: int
    name: str
    teacher_id: int
    teacher_name: str | None = None
    session_count: int = 0
    created_at: dt.datetime


class SessionCreateRequest(BaseModel):
    course_id: int = Field(gt=0)
    class_name: str = Field(min_length=1, max_length=60)
    room: str | None = Field(default=None, max_length=60)
    start_at: dt.datetime
    end_at: dt.datetime
    ai_threshold: float = Field(default=0.6, ge=0, le=1)

    @field_validator("class_name")
    @classmethod
    def _normalize_class_name(cls, value: str) -> str:
        return normalize_class_name(value)

    @model_validator(mode="after")
    def _check_window(self) -> "SessionCreateRequest":
        start = _ensure_aware(self.start_at)
        end = _ensure_aware(self.end_at)
        if end <= start:
            raise ValueError("结束时间必须晚于开始时间")
        self.start_at = start
        self.end_at = end
        return self


class SessionUpdateRequest(BaseModel):
    class_name: str | None = Field(default=None, min_length=1, max_length=60)
    room: str | None = Field(default=None, max_length=60)
    start_at: dt.datetime | None = None
    end_at: dt.datetime | None = None
    ai_threshold: float | None = Field(default=None, ge=0, le=1)
    cancelled: bool | None = None

    @field_validator("class_name")
    @classmethod
    def _normalize_class_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_class_name(value)

    @field_validator("start_at", "end_at")
    @classmethod
    def _require_aware(cls, value: dt.datetime | None) -> dt.datetime | None:
        if value is None:
            return None
        return _ensure_aware(value)


class SessionOut(BaseModel):
    id: int
    course_id: int
    course_name: str
    teacher_id: int
    teacher_name: str
    class_name: str
    room: str | None = None
    start_at: dt.datetime
    end_at: dt.datetime
    cancelled: bool
    ai_threshold: float
    status: SessionStatus
    member_count: int = 0
    manual_count: int = 0
    ai_count: int = 0


class MemberOut(BaseModel):
    user_id: int
    username: str
    arranged_at: dt.datetime | None = None


class MembersUpdateRequest(BaseModel):
    user_ids: list[int] = Field(default_factory=list, max_length=500)


class MembersOut(BaseModel):
    session_id: int
    member_count: int
    items: list[MemberOut] = Field(default_factory=list)


def _ensure_aware(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        raise ValueError("时间必须携带时区偏移量")
    return value.astimezone(dt.timezone.utc)
