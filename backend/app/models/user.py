"""用户实体。"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntType, UTCDateTime, utcnow
from app.models.enums import Role, UserStatus


def enum_type(enum_cls: type, name: str) -> SAEnum:
    """统一使用非原生枚举，落库为字符串加 CHECK 约束，便于 SQLite 与 MySQL 互转。"""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=32,
        create_constraint=True,
        values_callable=lambda members: [member.value for member in members],
        validate_strings=True,
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(enum_type(Role, "role_enum"), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[UserStatus] = mapped_column(
        enum_type(UserStatus, "user_status_enum"),
        nullable=False,
        default=UserStatus.ACTIVE,
        index=True,
    )
    auth_version: Mapped[int] = mapped_column(default=1, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utcnow
    )

    courses: Mapped[list["Course"]] = relationship(back_populates="teacher")  # noqa: F821

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"<User {self.id} {self.username} {self.role}>"


if TYPE_CHECKING:  # pragma: no cover
    from app.models.catalog import Course
