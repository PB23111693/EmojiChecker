"""认证接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.context import ok
from app.core.deps import get_current_user
from app.core.ratelimit import login_limiter
from app.db.base import get_db
from app.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenOut,
    UserOut,
)
from app.schemas.common import ApiResponse, MessageData
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


@router.post("/register", response_model=ApiResponse[UserOut], status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    user = AuthService(db).register(payload)
    return ok(user, "注册成功")


@router.post("/login", response_model=ApiResponse[TokenOut])
def login(
    payload: LoginRequest, request: Request, db: Session = Depends(get_db)
) -> dict:
    client = request.client.host if request.client else "-"
    login_limiter.check(f"{client}:{payload.username}")
    token = AuthService(db).login(payload)
    return ok(token, "登录成功")


@router.put("/password", response_model=ApiResponse[MessageData])
def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    AuthService(db).change_password(user, payload)
    return ok({"detail": "密码已修改，请使用新密码重新登录"}, "密码已修改")
