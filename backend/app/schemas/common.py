"""通用响应结构。"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: T | None = None
    request_id: str = ""


class PageData(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    page: int = 1
    page_size: int = 20
    total: int = 0


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageData(BaseModel):
    detail: str = ""
