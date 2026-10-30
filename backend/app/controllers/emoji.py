"""表情记录接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.context import ok, paginated
from app.core.deps import get_current_user, require_staff, require_student
from app.core.errors import RateLimited
from app.core.ratelimit import emoji_limiter
from app.core.realtime import hub
from app.db.base import get_db
from app.models import User
from app.repositories.emoji_repo import EmojiFilters
from app.schemas.common import ApiResponse, PageData
from app.schemas.emoji import EmojiRecordOut, EmojiSubmitRequest, EmojiSubmitResult
from app.services.emoji_service import EmojiService
from app.controllers.params import emoji_filters

router = APIRouter(prefix="/api/v1", tags=["表情记录"])


@router.post("/emoji", response_model=ApiResponse[EmojiSubmitResult])
def submit_emoji(
    payload: EmojiSubmitRequest,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> dict:
    emoji_limiter.check(f"emoji:{user.id}")
    result = EmojiService(db).submit(user, payload)
    if not result.duplicate:
        hub.publish_nowait(
            payload.session_id,
            {
                "type": "emoji.created",
                "session_id": payload.session_id,
                "source": "MANUAL",
                "record_id": result.record_id,
            },
        )
    return ok(result, "提交成功" if not result.duplicate else "该次提交已处理")


@router.get("/emoji/history", response_model=ApiResponse[PageData[EmojiRecordOut]])
def emoji_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.default_page_size, ge=1, le=settings.max_page_size),
    filters: EmojiFilters = Depends(emoji_filters),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    items, total = EmojiService(db).history(
        user, filters=filters, page=page, page_size=page_size
    )
    return ok(paginated(items, page, page_size, total))


@router.get("/sessions/{session_id}/students", response_model=ApiResponse[list[dict]])
def session_students(
    session_id: int,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    return ok(EmojiService(db).session_students(session_id, user))
