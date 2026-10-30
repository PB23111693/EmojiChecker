"""AI 服务接口。使用独立服务密钥，不能使用用户令牌。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.context import ok
from app.core.deps import require_ai_key
from app.core.realtime import hub
from app.db.base import get_db
from app.schemas.ai import AiBatchRequest, AiBatchResponse, AiContextOut
from app.schemas.common import ApiResponse
from app.services.ai_service import AiService

router = APIRouter(prefix="/api/v1/ai", tags=["AI 推理"])


@router.get("/context", response_model=ApiResponse[AiContextOut])
def ai_context(
    session_id: int = Query(ge=1),
    device_id: str = Query(min_length=1, max_length=60),
    _: None = Depends(require_ai_key),
    db: Session = Depends(get_db),
) -> dict:
    return ok(AiService(db).context(session_id, device_id))


@router.post(
    "/emoji-results",
    response_model=ApiResponse[AiBatchResponse],
    dependencies=[Depends(require_ai_key)],
)
def ingest_results(payload: AiBatchRequest, db: Session = Depends(get_db)) -> dict:
    result = AiService(db).ingest(payload)
    if result.accepted:
        hub.publish_nowait(
            payload.session_id,
            {
                "type": "emoji.created",
                "session_id": payload.session_id,
                "source": "AI",
                "accepted": result.accepted,
            },
        )
    return ok(result, "批次已处理")
