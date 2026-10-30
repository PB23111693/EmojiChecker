"""看板、统计与导出接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.context import ok
from app.core.deps import get_current_user, require_admin, require_staff
from app.db.base import get_db
from app.models import User
from app.repositories.emoji_repo import EmojiFilters
from app.schemas.common import ApiResponse
from app.schemas.stats import DashboardOut, StatisticsOut
from app.services.export_service import ExportService
from app.services.stats_service import StatsService
from app.controllers.params import emoji_filters

router = APIRouter(prefix="/api/v1", tags=["统计与看板"])


@router.get("/dashboard/realtime", response_model=ApiResponse[DashboardOut])
def realtime_dashboard(
    session_id: int = Query(ge=1),
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    return ok(StatsService(db).dashboard(user, session_id))


@router.get("/statistics", response_model=ApiResponse[StatisticsOut])
def statistics(
    filters: EmojiFilters = Depends(emoji_filters),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return ok(StatsService(db).statistics(user, filters))


# 以下三个路径是指导书第五章示例路径的兼容别名，与规范路径调用同一服务，
# 不复制业务逻辑。规范路径以 /api/v1/statistics 与 /api/v1/dashboard/realtime 为准。
@router.get(
    "/admin/dashboard/realtime",
    response_model=ApiResponse[DashboardOut],
    include_in_schema=False,
)
def realtime_dashboard_compat(
    session_id: int = Query(ge=1),
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    return ok(StatsService(db).dashboard(user, session_id))


@router.get("/admin/statistics", response_model=ApiResponse[StatisticsOut], include_in_schema=False)
def statistics_admin_compat(
    filters: EmojiFilters = Depends(emoji_filters),
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    return ok(StatsService(db).statistics(user, filters))


@router.get("/emoji/statistics", response_model=ApiResponse[StatisticsOut], include_in_schema=False)
def statistics_emoji_compat(
    filters: EmojiFilters = Depends(emoji_filters),
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    return ok(StatsService(db).statistics(user, filters))


@router.get("/admin/emoji/export")
def export_emoji(
    filters: EmojiFilters = Depends(emoji_filters),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    payload, filename, rows = ExportService(db).export(user, filters)
    return Response(
        content=payload,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Rows": str(rows),
            "Access-Control-Expose-Headers": "Content-Disposition, X-Export-Rows, X-Request-Id",
        },
    )
