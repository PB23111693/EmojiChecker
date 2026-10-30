"""请求上下文。request_id 贯穿日志、响应体与响应头。"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

_request_id: ContextVar[str] = ContextVar("request_id", default="")


def set_request_id(value: str) -> None:
    _request_id.set(value)


def get_request_id() -> str:
    return _request_id.get()


def ok(data: Any = None, message: str = "ok", code: int = 0) -> dict[str, Any]:
    """统一成功响应结构，见设计方案 7.1。"""
    return {
        "code": code,
        "message": message,
        "data": data,
        "request_id": get_request_id(),
    }


def fail(
    code: int,
    message: str,
    errors: Any = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "data": None,
        "request_id": get_request_id(),
        "errors": errors,
    }


def paginated(items: list[Any], page: int, page_size: int, total: int) -> dict[str, Any]:
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
    }
