"""认证服务：注册、登录、改密。"""

from __future__ import annotations

import hmac

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import Conflict, Forbidden, InvalidCredentials, ValidationFailed
from app.core.security import (
    create_access_token,
    hash_password,
    needs_rehash,
    validate_password_strength,
    verify_password,
)
from app.models import Role, User, UserStatus
from app.repositories.audit_repo import AuditRepository
from app.repositories.user_repo import UserRepository
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest, TokenOut, UserOut


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.audit = AuditRepository(db)

    @staticmethod
    def _check_invite(expected: str, provided: str | None, role_label: str) -> None:
        if not expected:
            raise ValidationFailed(f"{role_label}自助注册未开放，请联系管理员创建账号")
        if not provided or not hmac.compare_digest(provided, expected):
            raise ValidationFailed(f"{role_label}邀请码不正确")

    def register(self, payload: RegisterRequest) -> UserOut:
        role = Role.STUDENT
        if payload.role == Role.TEACHER:
            self._check_invite(settings.teacher_invite_code, payload.invite_code, "教师")
            role = Role.TEACHER
        elif payload.role == Role.ADMIN:
            self._check_invite(settings.admin_invite_code, payload.invite_code, "管理员")
            role = Role.ADMIN

        if self.users.get_by_username(payload.username):
            raise Conflict("该用户名已被占用")

        problems = validate_password_strength(payload.password)
        if problems:
            raise ValidationFailed("; ".join(problems), errors=problems)

        try:
            user = self.users.create(
                username=payload.username,
                password_hash=hash_password(payload.password),
                role=role,
                email=payload.email,
            )
        except IntegrityError as exc:
            self.db.rollback()
            raise Conflict("该用户名已被占用") from exc

        self.audit.add(
            actor_id=user.id,
            action="USER_REGISTER",
            target_type="user",
            target_id=str(user.id),
            detail=f"role={role.value}",
        )
        self.db.commit()
        return UserOut.model_validate(user)

    def login(self, payload: LoginRequest) -> TokenOut:
        user = self.users.get_by_username(payload.username)
        if user is None:
            # 用户不存在与密码错误返回同一提示，避免账号枚举。
            raise InvalidCredentials()
        if not verify_password(payload.password, user.password_hash):
            self.audit.add(
                actor_id=user.id,
                action="USER_LOGIN",
                target_type="user",
                target_id=str(user.id),
                result="FAILURE",
                detail="密码错误",
            )
            self.db.commit()
            raise InvalidCredentials()
        if user.status != UserStatus.ACTIVE:
            raise Forbidden("账号已停用，请联系管理员")

        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(payload.password)

        token, expires_at = create_access_token(
            user_id=user.id, role=user.role.value, auth_version=user.auth_version
        )
        self.audit.add(
            actor_id=user.id, action="USER_LOGIN", target_type="user", target_id=str(user.id)
        )
        self.db.commit()
        return TokenOut(access_token=token, expires_at=expires_at, user=UserOut.model_validate(user))

    def change_password(self, user: User, payload: ChangePasswordRequest) -> None:
        if not verify_password(payload.old_password, user.password_hash):
            raise InvalidCredentials("原密码不正确")
        if payload.old_password == payload.new_password:
            raise ValidationFailed("新密码不能与原密码相同")
        problems = validate_password_strength(payload.new_password)
        if problems:
            raise ValidationFailed("; ".join(problems), errors=problems)

        user.password_hash = hash_password(payload.new_password)
        self.users.bump_auth_version(user)
        self.audit.add(
            actor_id=user.id,
            action="USER_CHANGE_PASSWORD",
            target_type="user",
            target_id=str(user.id),
        )
        self.db.commit()
