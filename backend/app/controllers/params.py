"""接口查询参数到领域筛选条件的转换。列表、统计、导出共用。"""

from __future__ import annotations

import datetime as dt

from fastapi import Query

from app.core.text import normalize_class_name
from app.models import Emotion, Source
from app.repositories.emoji_repo import EmojiFilters


def _normalize(value: dt.datetime | None) -> dt.datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


def emoji_filters(
    course_id: int | None = Query(default=None, ge=1),
    session_id: int | None = Query(default=None, ge=1),
    class_name: str | None = Query(default=None, max_length=60),
    from_at: dt.datetime | None = Query(default=None, alias="from"),
    to_at: dt.datetime | None = Query(default=None, alias="to"),
    source: Source | None = Query(default=None),
    user_id: int | None = Query(default=None, ge=1),
    emotion: Emotion | None = Query(default=None),
) -> EmojiFilters:
    return EmojiFilters(
        course_id=course_id,
        session_id=session_id,
        class_name=normalize_class_name(class_name) if class_name else None,
        from_at=_normalize(from_at),
        to_at=_normalize(to_at),
        source=source,
        user_id=user_id,
        emotion=emotion,
    )
