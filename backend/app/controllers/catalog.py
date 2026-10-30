"""课程、课堂与名单接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.context import ok, paginated
from app.core.text import normalize_class_name
from app.core.deps import get_current_user, require_admin, require_staff
from app.db.base import get_db
from app.models import SessionStatus, User
from app.schemas.catalog import (
    CourseCreateRequest,
    CourseOut,
    MembersOut,
    MembersUpdateRequest,
    SessionCreateRequest,
    SessionOut,
    SessionUpdateRequest,
)
from app.schemas.common import ApiResponse, PageData
from app.schemas.stats import ClassOption
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/api/v1", tags=["课程与课堂"])


@router.get("/courses", response_model=ApiResponse[list[CourseOut]])
def list_courses(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    return ok(CatalogService(db).list_courses(user))


@router.post("/admin/courses", response_model=ApiResponse[CourseOut], status_code=201)
def create_course(
    payload: CourseCreateRequest,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return ok(CatalogService(db).create_course(payload, actor), "课程已创建")


@router.get("/sessions", response_model=ApiResponse[PageData[SessionOut]])
def list_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.default_page_size, ge=1, le=settings.max_page_size),
    course_id: int | None = Query(default=None, ge=1),
    class_name: str | None = Query(default=None, max_length=60),
    status: SessionStatus | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    items, total = CatalogService(db).list_sessions(
        user,
        course_id=course_id,
        class_name=normalize_class_name(class_name) if class_name else None,
        status=status.value if status else None,
        page=page,
        page_size=page_size,
    )
    return ok(paginated(items, page, page_size, total))


@router.get("/sessions/{session_id}", response_model=ApiResponse[SessionOut])
def get_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return ok(CatalogService(db).get_session(session_id, user))


@router.post("/admin/sessions", response_model=ApiResponse[SessionOut], status_code=201)
def create_session(
    payload: SessionCreateRequest,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return ok(CatalogService(db).create_session(payload, actor), "课堂已创建")


@router.patch("/admin/sessions/{session_id}", response_model=ApiResponse[SessionOut])
def update_session(
    session_id: int,
    payload: SessionUpdateRequest,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return ok(CatalogService(db).update_session(session_id, payload, actor), "课堂已更新")


@router.get("/admin/sessions/{session_id}/members", response_model=ApiResponse[MembersOut])
def list_members(
    session_id: int,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> dict:
    return ok(CatalogService(db).list_members(session_id, user))


@router.put("/admin/sessions/{session_id}/members", response_model=ApiResponse[MembersOut])
def replace_members(
    session_id: int,
    payload: MembersUpdateRequest,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return ok(CatalogService(db).replace_members(session_id, payload.user_ids, actor), "名单已保存")


@router.post(
    "/admin/sessions/{session_id}/schedule",
    response_model=ApiResponse[MembersOut],
    include_in_schema=False,
)
def schedule_compat(
    session_id: int,
    payload: MembersUpdateRequest,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """指导书示例路径的兼容别名，与 PUT .../members 行为一致。"""
    return ok(CatalogService(db).replace_members(session_id, payload.user_ids, actor), "名单已保存")


@router.get("/admin/classes", response_model=ApiResponse[list[ClassOption]])
def list_classes(
    user: User = Depends(require_staff), db: Session = Depends(get_db)
) -> dict:
    return ok(CatalogService(db).class_options(user))
