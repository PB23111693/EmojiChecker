"""用户与管理员用户管理接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.context import ok, paginated
from app.core.deps import get_current_user, require_admin
from app.db.base import get_db
from app.models import Role, User, UserStatus
from app.repositories.catalog_repo import CourseRepository
from app.schemas.auth import UserCreateRequest, UserOut, UserStatusRequest
from app.schemas.common import ApiResponse, PageData
from app.services.user_service import UserAdminService

router = APIRouter(prefix="/api/v1", tags=["用户"])


@router.get("/users/me", response_model=ApiResponse[UserOut])
def read_me(user: User = Depends(get_current_user)) -> dict:
    return ok(UserOut.model_validate(user))


@router.get("/admin/users", response_model=ApiResponse[PageData[UserOut]])
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.default_page_size, ge=1, le=settings.max_page_size),
    role: Role | None = Query(default=None),
    status: UserStatus | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=40),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    items, total = UserAdminService(db).list_users(
        page=page, page_size=page_size, role=role, status=status, keyword=keyword
    )
    return ok(paginated(items, page, page_size, total))


@router.post("/admin/users", response_model=ApiResponse[UserOut], status_code=201)
def create_user(
    payload: UserCreateRequest,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return ok(UserAdminService(db).create_user(payload, actor), "创建成功")


@router.patch("/admin/users/{user_id}/status", response_model=ApiResponse[UserOut])
def update_user_status(
    user_id: int,
    payload: UserStatusRequest,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return ok(UserAdminService(db).set_status(user_id, payload.status, actor), "状态已更新")


@router.get("/admin/teachers", response_model=ApiResponse[list[UserOut]])
def list_teachers(
    _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> dict:
    teachers = CourseRepository(db).teachers()
    return ok([UserOut.model_validate(item) for item in teachers])
