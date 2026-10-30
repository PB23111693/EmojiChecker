"""表情记录数据访问。列表、统计与导出共用同一套筛选条件，避免口径分裂。"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from app.models import ClassSession, Course, EmojiRecord, Emotion, Source, User


@dataclass(slots=True)
class EmojiFilters:
    course_id: int | None = None
    session_id: int | None = None
    class_name: str | None = None
    from_at: dt.datetime | None = None
    to_at: dt.datetime | None = None
    source: Source | None = None
    user_id: int | None = None
    teacher_id: int | None = None
    emotion: Emotion | None = None


class EmojiRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_event_id(self, event_id: str) -> EmojiRecord | None:
        return self.db.scalar(select(EmojiRecord).where(EmojiRecord.event_id == event_id))

    def add(self, record: EmojiRecord) -> EmojiRecord:
        self.db.add(record)
        self.db.flush()
        return record

    def _joined(self) -> Select:
        return (
            select(EmojiRecord)
            .join(ClassSession, EmojiRecord.session_id == ClassSession.id)
            .join(Course, ClassSession.course_id == Course.id)
        )

    def _conditions(self, filters: EmojiFilters) -> list:
        conditions = []
        if filters.teacher_id is not None:
            conditions.append(Course.teacher_id == filters.teacher_id)
        if filters.course_id is not None:
            conditions.append(ClassSession.course_id == filters.course_id)
        if filters.session_id is not None:
            conditions.append(EmojiRecord.session_id == filters.session_id)
        if filters.class_name:
            conditions.append(ClassSession.class_name == filters.class_name)
        if filters.from_at is not None:
            conditions.append(EmojiRecord.observed_at >= filters.from_at)
        if filters.to_at is not None:
            conditions.append(EmojiRecord.observed_at < filters.to_at)
        if filters.source is not None:
            conditions.append(EmojiRecord.source == filters.source)
        if filters.user_id is not None:
            conditions.append(EmojiRecord.user_id == filters.user_id)
        if filters.emotion is not None:
            conditions.append(EmojiRecord.emotion == filters.emotion)
        return conditions

    def query(self, filters: EmojiFilters) -> Select:
        return self._joined().where(*self._conditions(filters))

    def paginate(
        self, filters: EmojiFilters, *, page: int, page_size: int
    ) -> tuple[list[EmojiRecord], int]:
        base = self.query(filters)
        total = int(
            self.db.scalar(
                select(func.count()).select_from(base.subquery())
            )
            or 0
        )
        stmt = (
            base.options(
                joinedload(EmojiRecord.session).joinedload(ClassSession.course),
                joinedload(EmojiRecord.user),
            )
            .order_by(EmojiRecord.observed_at.desc(), EmojiRecord.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.db.scalars(stmt)), total

    def total(self, filters: EmojiFilters) -> int:
        base = self.query(filters)
        return int(self.db.scalar(select(func.count()).select_from(base.subquery())) or 0)

    def count_by_source(self, filters: EmojiFilters) -> dict[str, int]:
        base = self.query(filters)
        subquery = base.with_only_columns(
            EmojiRecord.source.label("source"), EmojiRecord.id.label("id")
        ).subquery()
        stmt = select(subquery.c.source, func.count()).group_by(subquery.c.source)
        return {str(source): int(count) for source, count in self.db.execute(stmt).all()}

    def distribution(self, filters: EmojiFilters) -> dict[str, int]:
        base = self.query(filters)
        subquery = base.with_only_columns(
            EmojiRecord.emotion.label("emotion"), EmojiRecord.id.label("id")
        ).subquery()
        stmt = select(subquery.c.emotion, func.count()).group_by(subquery.c.emotion)
        return {str(emotion): int(count) for emotion, count in self.db.execute(stmt).all()}

    def participants(self, filters: EmojiFilters) -> int:
        # 参与人数只对 MANUAL 有意义；来源筛选为 AI 时应为 0，而不是回退到手动人数。
        source = Source.AI if filters.source == Source.AI else Source.MANUAL
        scoped = EmojiFilters(
            course_id=filters.course_id,
            session_id=filters.session_id,
            class_name=filters.class_name,
            from_at=filters.from_at,
            to_at=filters.to_at,
            source=source,
            user_id=filters.user_id,
            teacher_id=filters.teacher_id,
            emotion=filters.emotion,
        )
        base = self.query(scoped)
        subquery = base.with_only_columns(EmojiRecord.user_id.label("user_id")).subquery()
        stmt = select(func.count(func.distinct(subquery.c.user_id)))
        return int(self.db.scalar(stmt) or 0)

    def trend_rows(self, filters: EmojiFilters) -> list[tuple[dt.datetime, str]]:
        base = self.query(filters)
        subquery = base.with_only_columns(
            EmojiRecord.observed_at.label("observed_at"),
            EmojiRecord.source.label("source"),
        ).subquery()
        stmt = select(subquery.c.observed_at, subquery.c.source)
        return [(row[0], str(row[1])) for row in self.db.execute(stmt).all()]

    def iter_all(self, filters: EmojiFilters, *, limit: int = 50000) -> list[EmojiRecord]:
        stmt = (
            self.query(filters)
            .options(
                joinedload(EmojiRecord.session).joinedload(ClassSession.course),
                joinedload(EmojiRecord.user),
            )
            .order_by(EmojiRecord.observed_at.desc(), EmojiRecord.id.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def source_counts_by_session(self, session_ids: list[int]) -> dict[int, dict[str, int]]:
        if not session_ids:
            return {}
        stmt = (
            select(EmojiRecord.session_id, EmojiRecord.source, func.count())
            .where(EmojiRecord.session_id.in_(session_ids))
            .group_by(EmojiRecord.session_id, EmojiRecord.source)
        )
        result: dict[int, dict[str, int]] = {}
        for session_id, source, count in self.db.execute(stmt).all():
            result.setdefault(int(session_id), {})[str(source)] = int(count)
        return result

    def teacher_of(self, session_id: int) -> int | None:
        stmt = (
            select(Course.teacher_id)
            .join(ClassSession, ClassSession.course_id == Course.id)
            .where(ClassSession.id == session_id)
        )
        return self.db.scalar(stmt)

    def distinct_students(self, session_id: int) -> list[User]:
        stmt = (
            select(User)
            .join(EmojiRecord, EmojiRecord.user_id == User.id)
            .where(
                EmojiRecord.session_id == session_id,
                EmojiRecord.source == Source.MANUAL,
            )
            .distinct()
            .order_by(User.username)
        )
        return list(self.db.scalars(stmt))
