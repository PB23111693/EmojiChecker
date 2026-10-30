"""密码哈希与访问令牌。对应设计方案 7.3。"""

from __future__ import annotations

import datetime as dt
import re
import secrets
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings
from app.core.errors import Unauthorized

_hasher = PasswordHasher()
_ALGORITHM = "HS256"
_PASSWORD_MIN = 8
_PASSWORD_MAX = 64


def hash_password(raw_password: str) -> str:
    return _hasher.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, raw_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    except Exception:
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except Exception:
        return False


def validate_password_strength(raw_password: str) -> list[str]:
    """返回不满足项的中文说明，空列表表示通过。"""
    problems: list[str] = []
    if not _PASSWORD_MIN <= len(raw_password) <= _PASSWORD_MAX:
        problems.append(f"密码长度需在 {_PASSWORD_MIN} 至 {_PASSWORD_MAX} 个字符之间")
    if not re.search(r"[A-Za-z]", raw_password):
        problems.append("密码需包含字母")
    if not re.search(r"\d", raw_password):
        problems.append("密码需包含数字")
    return problems


def create_access_token(
    *,
    user_id: int,
    role: str,
    auth_version: int,
    expires_minutes: int | None = None,
    now: dt.datetime | None = None,
) -> tuple[str, dt.datetime]:
    issued_at = now or dt.datetime.now(dt.timezone.utc)
    minutes = expires_minutes or settings.access_token_minutes
    expires_at = issued_at + dt.timedelta(minutes=minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "av": auth_version,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": secrets.token_hex(8),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM)
    return token, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise Unauthorized("登录已过期，请重新登录") from exc
    except jwt.InvalidTokenError as exc:
        raise Unauthorized("登录凭证无效") from exc
    return payload
