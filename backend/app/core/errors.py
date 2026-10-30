"""业务异常与错误码。HTTP 状态码与业务码同时返回，两者语义一致。"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """所有可预期业务异常的基类。"""

    code: int = 40000
    status_code: int = 400
    default_message: str = "请求无法处理"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: int | None = None,
        status_code: int | None = None,
        errors: Any = None,
    ) -> None:
        self.message = message or self.default_message
        self.code = code or type(self).code
        self.status_code = status_code or type(self).status_code
        self.errors = errors
        super().__init__(self.message)


class InvalidCredentials(AppError):
    code = 40101
    status_code = 401
    default_message = "用户名或密码错误"


class Unauthorized(AppError):
    code = 40100
    status_code = 401
    default_message = "登录状态无效或已过期"


class Forbidden(AppError):
    code = 40300
    status_code = 403
    default_message = "没有权限执行该操作"


class NotFound(AppError):
    code = 40400
    status_code = 404
    default_message = "对象不存在或不在可见范围内"


class Conflict(AppError):
    code = 40900
    status_code = 409
    default_message = "操作与当前状态冲突"


class ValidationFailed(AppError):
    code = 42200
    status_code = 422
    default_message = "请求参数不合法"


class RateLimited(AppError):
    code = 42900
    status_code = 429
    default_message = "请求过于频繁，请稍后再试"


class ServiceUnavailable(AppError):
    code = 50300
    status_code = 503
    default_message = "服务暂时不可用"
