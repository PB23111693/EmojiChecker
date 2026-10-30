"""用户数据访问。"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Role, User, UserStatus


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        return self.db.scalar(select(User).where(User.username == username))

    def create(
        self,
        *,
        username: str,
        password_hash: str,
        role: Role,
        email: str | None = None,
    ) -> User:
        user = User(
            username=username,
            password_hash=password_hash,
            role=role,
            email=email,
            status=UserStatus.ACTIVE,
            auth_version=1,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def list(
        self,
        *,
        page: int,
        page_size: int,
        role: Role | None = None,
        status: UserStatus | None = None,
        keyword: str | None = None,
    ) -> tuple[list[User], int]:
        conditions = []
        if role is not None:
            conditions.append(User.role == role)
        if status is not None:
            conditions.append(User.status == status)
        if keyword:
            like = f"%{keyword.strip()}%"
            conditions.append(or_(User.username.like(like), User.email.like(like)))

        total = self.db.scalar(select(func.count()).select_from(User).where(*conditions)) or 0
        stmt = (
            select(User)
            .where(*conditions)
            .order_by(User.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.db.scalars(stmt)), int(total)

    def list_by_ids(self, user_ids: list[int]) -> list[User]:
        if not user_ids:
            return []
        return list(self.db.scalars(select(User).where(User.id.in_(user_ids))))

    def count_active_admins(self, exclude_id: int | None = None) -> int:
        stmt = select(func.count()).select_from(User).where(
            User.role == Role.ADMIN, User.status == UserStatus.ACTIVE
        )
        if exclude_id is not None:
            stmt = stmt.where(User.id != exclude_id)
        return int(self.db.scalar(stmt) or 0)

    def bump_auth_version(self, user: User) -> None:
        user.auth_version += 1
        self.db.flush()
