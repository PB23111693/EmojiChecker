"""审计日志接口。仅管理员可查，用于追溯建号、名单变更、停用与导出。"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.context import ok, paginated
from app.core.deps import require_admin
from app.db.base import get_db
from app.models import User
from app.repositories.audit_repo import AuditRepository
from app.schemas.common import ApiResponse, PageData

router = APIRouter(prefix="/api/v1/admin", tags=["审计日志"])


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None = None
    action: str
    target_type: str | None = None
    target_id: str | None = None
    result: str
    detail: str | None = None
    created_at: dt.datetime


@router.get("/audit-logs", response_model=ApiResponse[PageData[AuditLogOut]])
def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.default_page_size, ge=1, le=settings.max_page_size),
    action: str | None = Query(default=None, max_length=60),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    rows, total = AuditRepository(db).list(page=page, page_size=page_size, action=action)
    return ok(paginated([AuditLogOut.model_validate(row) for row in rows], page, page_size, total))
