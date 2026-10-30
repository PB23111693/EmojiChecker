"""手动反馈服务。幂等、时间片与名单校验集中在此。"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.db.base import utcnow
from app.models import EmojiRecord, Role, SessionStatus, Source, User, compute_session_status
from app.repositories.audit_repo import AuditRepository
from app.repositories.catalog_repo import SessionRepository
from app.repositories.emoji_repo import EmojiFilters, EmojiRepository
from app.repositories.user_repo import UserRepository
from app.schemas.emoji import EmojiRecordOut, EmojiSubmitRequest, EmojiSubmitResult


class EmojiService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.sessions = SessionRepository(db)
        self.emoji = EmojiRepository(db)
        self.users = UserRepository(db)
        self.audit = AuditRepository(db)

    def submit(self, user: User, payload: EmojiSubmitRequest) -> EmojiSubmitResult:
        session = self.sessions.get(payload.session_id)
        if session is None:
            raise NotFound("课堂不存在")
        if not self.sessions.is_member(session.id, user.id):
            raise Forbidden("你不在该课堂的参与名单中")

        # 先确认已成功事件的幂等结果，再判断课堂状态。学生在结束前提交成功、
        # 但响应丢失，结束后原样重试时应返回原记录，而不是被“课堂已结束”拒绝。
        existing = self.emoji.get_by_event_id(payload.event_id)
        if existing is not None:
            if self._same_manual_event(existing, payload, user):
                return EmojiSubmitResult(
                    record_id=existing.id, observed_at=existing.observed_at, duplicate=True
                )
            raise Conflict("事件编号已被占用且内容不一致")

        now = utcnow()
        status = compute_session_status(session.start_at, session.end_at, session.cancelled, now)
        if status == SessionStatus.CANCELLED:
            raise Conflict("课堂已取消，不能提交反馈")
        if status == SessionStatus.PENDING:
            raise Conflict("课堂尚未开始，不能提交反馈")
        if status == SessionStatus.ENDED:
            raise Conflict("课堂已结束，不能提交反馈")

        slot: int | None = None
        if settings.manual_slot_seconds > 0:
            slot = int(now.timestamp()) // settings.manual_slot_seconds

        record = EmojiRecord(
            event_id=payload.event_id,
            session_id=session.id,
            user_id=user.id,
            emotion=payload.emotion,
            source=Source.MANUAL,
            confidence=None,
            device_id=None,
            model_version=None,
            observed_at=now,
            received_at=now,
            manual_slot=slot,
        )
        self.db.add(record)
        try:
            self.db.commit()
        except IntegrityError:
            # 并发下 event_id 或时间片唯一约束可能同时触发。回滚后重查：
            # 同一事件内容一致视为幂等成功，内容不一致或占用时间片才返回冲突。
            self.db.rollback()
            existing = self.emoji.get_by_event_id(payload.event_id)
            if existing is not None:
                if self._same_manual_event(existing, payload, user):
                    return EmojiSubmitResult(
                        record_id=existing.id,
                        observed_at=existing.observed_at,
                        duplicate=True,
                    )
                raise Conflict("事件编号已被占用且内容不一致")
            if slot is not None:
                raise Conflict(
                    f"同一课堂每 {settings.manual_slot_seconds} 秒只能提交一次，请稍后再试"
                )
            raise Conflict("提交与已有记录冲突")

        return EmojiSubmitResult(
            record_id=record.id, observed_at=record.observed_at, duplicate=False
        )

    @staticmethod
    def _same_manual_event(
        existing: EmojiRecord, payload: EmojiSubmitRequest, user: User
    ) -> bool:
        return (
            existing.source == Source.MANUAL
            and existing.user_id == user.id
            and existing.session_id == payload.session_id
            and existing.emotion == payload.emotion
        )

    def history(
        self,
        user: User,
        *,
        filters: EmojiFilters,
        page: int,
        page_size: int,
    ) -> tuple[list[EmojiRecordOut], int]:
        scoped = EmojiFilters(
            course_id=filters.course_id,
            session_id=filters.session_id,
            class_name=filters.class_name,
            from_at=filters.from_at,
            to_at=filters.to_at,
            source=filters.source,
            user_id=filters.user_id,
            teacher_id=filters.teacher_id,
            emotion=filters.emotion,
        )
        if user.role == Role.STUDENT:
            # 学生只能看本人手动记录，调用方传入的任何范围参数都会被覆盖。
            scoped.user_id = user.id
            scoped.source = Source.MANUAL
            scoped.teacher_id = None
        elif user.role == Role.TEACHER:
            scoped.teacher_id = user.id
            if scoped.user_id is not None and scoped.session_id is None:
                raise ValidationFailed("按学生查询时必须指定课堂")
        else:
            scoped.teacher_id = None

        rows, total = self.emoji.paginate(scoped, page=page, page_size=page_size)
        return [self._to_out(row) for row in rows], total

    def session_students(self, session_id: int, user: User) -> list[dict[str, object]]:
        session = self.sessions.get(session_id)
        if session is None:
            raise NotFound("课堂不存在")
        if user.role == Role.TEACHER and session.course.teacher_id != user.id:
            raise NotFound("课堂不存在")
        students = self.emoji.distinct_students(session_id)
        counts = self._manual_counts_by_user(session_id)
        return [
            {
                "user_id": item.id,
                "username": item.username,
                "record_count": counts.get(item.id, 0),
            }
            for item in students
        ]

    def _manual_counts_by_user(self, session_id: int) -> dict[int, int]:
        from sqlalchemy import func, select

        stmt = (
            select(EmojiRecord.user_id, func.count())
            .where(
                EmojiRecord.session_id == session_id,
                EmojiRecord.source == Source.MANUAL,
                EmojiRecord.user_id.is_not(None),
            )
            .group_by(EmojiRecord.user_id)
        )
        return {int(uid): int(count) for uid, count in self.db.execute(stmt).all()}

    def _to_out(self, row: EmojiRecord) -> EmojiRecordOut:
        return EmojiRecordOut(
            id=row.id,
            event_id=row.event_id,
            session_id=row.session_id,
            course_name=row.session.course.name,
            class_name=row.session.class_name,
            user_id=row.user_id,
            username=row.user.username if row.user else None,
            emotion=row.emotion,
            source=row.source,
            confidence=row.confidence,
            device_id=row.device_id,
            observed_at=row.observed_at,
            received_at=row.received_at,
        )
