"""管理员用户管理服务。"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.security import hash_password, validate_password_strength
from app.models import Role, User, UserStatus
from app.repositories.audit_repo import AuditRepository
from app.repositories.user_repo import UserRepository
from app.schemas.auth import UserCreateRequest, UserOut


class UserAdminService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.audit = AuditRepository(db)

    def list_users(
        self,
        *,
        page: int,
        page_size: int,
        role: Role | None,
        status: UserStatus | None,
        keyword: str | None,
    ) -> tuple[list[UserOut], int]:
        items, total = self.users.list(
            page=page, page_size=page_size, role=role, status=status, keyword=keyword
        )
        return [UserOut.model_validate(item) for item in items], total

    def create_user(self, payload: UserCreateRequest, actor: User) -> UserOut:
        if self.users.get_by_username(payload.username):
            raise Conflict("该用户名已被占用")
        problems = validate_password_strength(payload.password)
        if problems:
            raise ValidationFailed("; ".join(problems), errors=problems)
        try:
            user = self.users.create(
                username=payload.username,
                password_hash=hash_password(payload.password),
                role=payload.role,
                email=payload.email,
            )
        except IntegrityError as exc:
            self.db.rollback()
            raise Conflict("该用户名已被占用") from exc

        self.audit.add(
            actor_id=actor.id,
            action="ADMIN_CREATE_USER",
            target_type="user",
            target_id=str(user.id),
            detail=f"role={payload.role.value}",
        )
        self.db.commit()
        return UserOut.model_validate(user)

    def set_status(self, user_id: int, status: UserStatus, actor: User) -> UserOut:
        user = self.users.get(user_id)
        if user is None:
            raise NotFound("用户不存在")
        if user.id == actor.id and status == UserStatus.DISABLED:
            raise Conflict("不能停用当前登录的管理员账号")
        if (
            user.role == Role.ADMIN
            and status == UserStatus.DISABLED
            and self.users.count_active_admins(exclude_id=user.id) == 0
        ):
            raise Conflict("系统必须保留至少一名启用状态的管理员")

        user.status = status
        # 停用或重新启用都递增令牌版本，确保已有会话立即失效。
        self.users.bump_auth_version(user)
        self.audit.add(
            actor_id=actor.id,
            action="ADMIN_SET_USER_STATUS",
            target_type="user",
            target_id=str(user.id),
            detail=status.value,
        )
        self.db.commit()
        return UserOut.model_validate(user)
