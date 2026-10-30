"""认证与用户相关数据结构。"""

from __future__ import annotations

import datetime as dt
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import Role, UserStatus

USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,31}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Role
    email: str | None = None
    status: UserStatus
    created_at: dt.datetime


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=64)
    email: str | None = Field(default=None, max_length=120)
    role: Role | None = Field(
        default=None,
        description="学生可省略；TEACHER 与 ADMIN 必须携带对应邀请码，其他取值返回 422",
    )
    invite_code: str | None = Field(default=None, max_length=64)

    @field_validator("username")
    @classmethod
    def _check_username(cls, value: str) -> str:
        if not USERNAME_PATTERN.match(value):
            raise ValueError("用户名需以字母开头，仅含字母、数字与下划线，长度 3 至 32")
        return value

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not EMAIL_PATTERN.match(value):
            raise ValueError("邮箱格式不正确")
        return value

    @field_validator("role")
    @classmethod
    def _check_role(cls, value: Role | None) -> Role | None:
        # 学生注册不需要 role 字段；教师与管理员必须凭各自邀请码，服务层校验邀请码。
        if value is None or value == Role.STUDENT:
            return None
        return value


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=64)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: dt.datetime
    user: UserOut


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=64)
    new_password: str = Field(min_length=8, max_length=64)


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=64)
    role: Role = Field(description="管理员可创建 TEACHER 或 STUDENT")
    email: str | None = Field(default=None, max_length=120)

    @field_validator("username")
    @classmethod
    def _check_username(cls, value: str) -> str:
        if not USERNAME_PATTERN.match(value):
            raise ValueError("用户名需以字母开头，仅含字母、数字与下划线，长度 3 至 32")
        return value

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not EMAIL_PATTERN.match(value):
            raise ValueError("邮箱格式不正确")
        return value

    @field_validator("role")
    @classmethod
    def _check_role(cls, value: Role) -> Role:
        if value == Role.ADMIN:
            raise ValueError("管理员账号请通过管理员注册入口或初始化脚本创建")
        return value


class UserStatusRequest(BaseModel):
    status: UserStatus
