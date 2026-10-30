"""AI 结果入库服务。匿名、幂等、阈值与时钟偏差校验见设计方案 7.2 与 8.3。"""

from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import Forbidden, NotFound
from app.db.base import utcnow
from app.models import (
    ClassSession,
    EmojiRecord,
    SessionStatus,
    Source,
    compute_session_status,
)
from app.repositories.catalog_repo import SessionRepository
from app.repositories.emoji_repo import EmojiRepository
from app.schemas.ai import AiBatchRequest, AiBatchResponse, AiContextOut, AiEventResult

logger = logging.getLogger(__name__)

EMOTIONS = [
    "HAPPY",
    "NEUTRAL",
    "SAD",
    "ANGRY",
    "SURPRISED",
    "FEARFUL",
    "DISGUST",
]


def _as_utc(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


class AiService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.sessions = SessionRepository(db)
        self.emoji = EmojiRepository(db)

    def _session(self, session_id: int) -> ClassSession:
        session = self.sessions.get(session_id)
        if session is None:
            raise NotFound("课堂不存在")
        return session

    def context(self, session_id: int, device_id: str) -> AiContextOut:
        if settings.ai_device_id and device_id != settings.ai_device_id:
            raise Forbidden("设备标识与服务密钥不匹配")
        session = self._session(session_id)
        if session.course.teacher_id is None:
            raise Forbidden("课堂未绑定课程")
        if settings.ai_allowed_session_ids and session.id not in settings.ai_allowed_session_ids:
            raise Forbidden("该服务密钥未被授权访问此课堂")
        status = compute_session_status(session.start_at, session.end_at, session.cancelled)
        return AiContextOut(
            session_id=session.id,
            course_name=session.course.name,
            class_name=session.class_name,
            start_at=session.start_at,
            end_at=session.end_at,
            status=status.value,
            ai_threshold=session.ai_threshold,
            emotions=EMOTIONS,
        )

    def ingest(self, payload: AiBatchRequest) -> AiBatchResponse:
        if settings.ai_device_id and payload.device_id != settings.ai_device_id:
            raise Forbidden("设备标识与服务密钥不匹配")
        if settings.ai_allowed_session_ids and payload.session_id not in settings.ai_allowed_session_ids:
            raise Forbidden("该服务密钥未被授权访问此课堂")

        session = self._session(payload.session_id)
        now = utcnow()
        status = compute_session_status(session.start_at, session.end_at, session.cancelled, now)
        session_open = status == SessionStatus.ONGOING

        response = AiBatchResponse()
        for item in payload.results:
            observed_at = _as_utc(item.observed_at)
            existing = self.emoji.get_by_event_id(item.event_id)
            if existing is not None:
                if self._same_event(existing, payload, item, observed_at):
                    response.duplicates += 1
                    response.details.append(
                        AiEventResult(
                            event_id=item.event_id, status="DUPLICATE", record_id=existing.id
                        )
                    )
                else:
                    response.rejected += 1
                    response.details.append(
                        AiEventResult(
                            event_id=item.event_id, status="REJECTED", reason="EVENT_ID_CONFLICT"
                        )
                    )
                continue

            reason = self._validate_new_event(session, session_open, item, observed_at, now)
            if reason is not None:
                response.rejected += 1
                response.details.append(
                    AiEventResult(event_id=item.event_id, status="REJECTED", reason=reason)
                )
                continue

            try:
                with self.db.begin_nested():
                    record = EmojiRecord(
                        event_id=item.event_id,
                        session_id=session.id,
                        user_id=None,
                        emotion=item.emotion,
                        source=Source.AI,
                        confidence=item.confidence,
                        device_id=payload.device_id,
                        model_version=payload.model_version,
                        observed_at=observed_at,
                        received_at=now,
                        manual_slot=None,
                    )
                    self.db.add(record)
                response.accepted += 1
                response.details.append(
                    AiEventResult(
                        event_id=item.event_id, status="ACCEPTED", record_id=record.id
                    )
                )
            except IntegrityError:
                response.rejected += 1
                response.details.append(
                    AiEventResult(
                        event_id=item.event_id, status="REJECTED", reason="EVENT_ID_CONFLICT"
                    )
                )

        self.db.commit()
        logger.info(
            "ai batch ingested session=%s device=%s accepted=%s duplicates=%s rejected=%s",
            session.id,
            payload.device_id,
            response.accepted,
            response.duplicates,
            response.rejected,
        )
        return response

    def _validate_new_event(
        self,
        session: ClassSession,
        session_open: bool,
        item,
        observed_at: dt.datetime,
        now: dt.datetime,
    ) -> str | None:
        if not session_open:
            return "SESSION_NOT_ONGOING"
        if observed_at < session.start_at or observed_at >= session.end_at:
            return "OUT_OF_SESSION_WINDOW"
        if observed_at < now - dt.timedelta(seconds=settings.ai_max_past_seconds):
            return "OBSERVED_TOO_OLD"
        if observed_at > now + dt.timedelta(seconds=settings.ai_max_future_seconds):
            return "OBSERVED_IN_FUTURE"
        if item.confidence < session.ai_threshold:
            return "BELOW_THRESHOLD"
        return None

    def _same_event(
        self, existing: EmojiRecord, payload: AiBatchRequest, item, observed_at: dt.datetime
    ) -> bool:
        return (
            existing.source == Source.AI
            and existing.session_id == payload.session_id
            and existing.device_id == payload.device_id
            and existing.emotion == item.emotion
            and abs(existing.observed_at - observed_at) < dt.timedelta(milliseconds=1)
            and abs((existing.confidence or 0) - item.confidence) < 1e-9
        )
