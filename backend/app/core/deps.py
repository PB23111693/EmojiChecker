"""请求依赖：身份解析、角色校验与 AI 服务密钥校验。"""

from __future__ import annotations

import hmac

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import Forbidden, Unauthorized
from app.core.security import decode_access_token
from app.db.base import get_db
from app.models import Role, User, UserStatus

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise Unauthorized("请先登录")
    payload = decode_access_token(credentials.credentials)
    try:
        user_id = int(payload.get("sub", "0"))
    except (TypeError, ValueError) as exc:
        raise Unauthorized("登录凭证无效") from exc

    user = db.get(User, user_id)
    if user is None:
        raise Unauthorized("账号不存在")
    if user.status != UserStatus.ACTIVE:
        raise Unauthorized("账号已停用，请重新登录")
    # 令牌版本与服务端不一致说明期间发生过改密或启停，旧令牌立即失效。
    if int(payload.get("av", -1)) != user.auth_version:
        raise Unauthorized("登录已失效，请重新登录")
    if payload.get("role") != user.role.value:
        raise Unauthorized("登录已失效，请重新登录")
    return user


def require_roles(*roles: Role):
    allowed = set(roles)

    def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise Forbidden()
        return user

    return _dependency


require_admin = require_roles(Role.ADMIN)
require_staff = require_roles(Role.ADMIN, Role.TEACHER)
require_student = require_roles(Role.STUDENT)


def require_ai_key(
    x_ai_service_key: str | None = Header(default=None, alias="X-AI-Service-Key"),
) -> None:
    expected = settings.ai_service_key
    if not x_ai_service_key or not expected:
        raise Unauthorized("AI 服务密钥缺失")
    if not hmac.compare_digest(x_ai_service_key, expected):
        raise Unauthorized("AI 服务密钥无效")
