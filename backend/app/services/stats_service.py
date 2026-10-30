"""统计与看板服务。手动与 AI 分别计算，不合并成单一情绪得分。"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.db.base import utcnow
from app.models import Emotion, Role, User, compute_session_status
from app.repositories.catalog_repo import SessionRepository
from app.repositories.emoji_repo import EmojiFilters, EmojiRepository
from app.schemas.stats import (
    AiBlock,
    DashboardOut,
    EmotionCount,
    ManualBlock,
    StatisticsOut,
    TrendPoint,
)


def _local_tz() -> dt.tzinfo:
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("Asia/Shanghai")
    except Exception:
        # Windows 缺少 tzdata 时退化为固定东八区。上海自 1991 年后不再使用夏令时。
        return dt.timezone(dt.timedelta(hours=8))


def _ratio(part: int, total: int) -> float:
    return round(part / total, 4) if total else 0.0


def _distribution(counts: dict[str, int], total: int) -> list[EmotionCount]:
    items = [
        EmotionCount(emotion=Emotion(value), count=count, ratio=_ratio(count, total))
        for value, count in counts.items()
    ]
    return sorted(items, key=lambda item: (-item.count, item.emotion.value))


def _pick_step(span_minutes: int) -> int:
    for step in (1, 5, 15, 30, 60):
        if span_minutes / step <= 240:
            return step
    return 60


def build_trend(rows: list[tuple[dt.datetime, str]], granularity: int | None = None) -> list[TrendPoint]:
    """按观测时间分桶。空桶补 0，仅覆盖数据实际跨越的区间，避免生成无意义的超长序列。"""
    if not rows:
        return []
    tz = _local_tz()
    local_rows = [(observed.astimezone(tz), source) for observed, source in rows]
    minutes = [int(item[0].timestamp() // 60) for item in local_rows]
    span = max(minutes) - min(minutes) + 1
    step = granularity or _pick_step(span)

    buckets: dict[int, dict[str, int]] = defaultdict(lambda: {"MANUAL": 0, "AI": 0})
    for (observed, source), minute in zip(local_rows, minutes, strict=True):
        bucket_minute = (minute // step) * step
        buckets[bucket_minute][source] = buckets[bucket_minute].get(source, 0) + 1

    start = (min(minutes) // step) * step
    end = max(minutes)
    points: list[TrendPoint] = []
    cursor = start
    same_day = dt.datetime.fromtimestamp(start * 60, tz).date() == dt.datetime.fromtimestamp(
        end * 60, tz
    ).date()
    fmt = "%H:%M" if same_day else "%m-%d %H:%M"
    while cursor <= end:
        bucket = buckets.get(cursor, {"MANUAL": 0, "AI": 0})
        points.append(
            TrendPoint(
                bucket=dt.datetime.fromtimestamp(cursor * 60, tz).strftime(fmt),
                manual=int(bucket.get("MANUAL", 0)),
                ai=int(bucket.get("AI", 0)),
            )
        )
        cursor += step
    return points


class StatsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.sessions = SessionRepository(db)
        self.emoji = EmojiRepository(db)

    def dashboard(self, user: User, session_id: int) -> DashboardOut:
        session = self.sessions.get(session_id)
        if session is None:
            raise NotFound("课堂不存在")
        if user.role == Role.TEACHER and session.course.teacher_id != user.id:
            raise NotFound("课堂不存在")

        now = utcnow()
        status = compute_session_status(session.start_at, session.end_at, session.cancelled, now)
        base = EmojiFilters(session_id=session.id)

        manual_filters = EmojiFilters(session_id=session.id, source="MANUAL")
        ai_filters = EmojiFilters(session_id=session.id, source="AI")

        manual_counts = self.emoji.distribution(manual_filters)
        manual_total = sum(manual_counts.values())
        ai_counts = self.emoji.distribution(ai_filters)
        ai_total = sum(ai_counts.values())
        member_count = self.sessions.member_count(session.id)
        participants = self.emoji.participants(manual_filters)

        rows = self.emoji.trend_rows(base)
        last_ai = max((item for item, source in rows if source == "AI"), default=None)

        return DashboardOut(
            session_id=session.id,
            course_name=session.course.name,
            class_name=session.class_name,
            status=status.value,
            manual=ManualBlock(
                total=manual_total,
                participants=participants,
                member_count=member_count,
                coverage=_ratio(participants, member_count) if member_count else None,
                distribution=_distribution(manual_counts, manual_total),
            ),
            ai=AiBlock(
                total=ai_total,
                threshold=session.ai_threshold,
                last_observed_at=last_ai,
                distribution=_distribution(ai_counts, ai_total),
            ),
            trend=build_trend(rows),
            last_update_at=now,
        )

    def statistics(self, user: User, filters: EmojiFilters) -> StatisticsOut:
        scoped = EmojiFilters(
            course_id=filters.course_id,
            session_id=filters.session_id,
            class_name=filters.class_name,
            from_at=filters.from_at,
            to_at=filters.to_at,
            source=filters.source,
            user_id=filters.user_id,
            teacher_id=user.id if user.role == Role.TEACHER else None,
            emotion=filters.emotion,
        )
        if user.role == Role.STUDENT:
            raise NotFound("接口不可用")

        total = self.emoji.total(scoped)
        by_source = self.emoji.count_by_source(scoped)
        distribution = self.emoji.distribution(scoped)
        participants = self.emoji.participants(scoped)

        return StatisticsOut(
            total=total,
            manual_total=int(by_source.get("MANUAL", 0)),
            ai_total=int(by_source.get("AI", 0)),
            participants=participants,
            distribution=_distribution(distribution, total),
            by_source={key: int(value) for key, value in by_source.items()},
            trend=build_trend(self.emoji.trend_rows(scoped)),
            filters={
                "course_id": str(scoped.course_id) if scoped.course_id else None,
                "session_id": str(scoped.session_id) if scoped.session_id else None,
                "class_name": scoped.class_name,
                "from": scoped.from_at.isoformat() if scoped.from_at else None,
                "to": scoped.to_at.isoformat() if scoped.to_at else None,
                "source": scoped.source,
            },
        )
