"""后端 AI 接口客户端。使用独立服务密钥，不使用用户令牌。"""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class ApiError(RuntimeError):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


class AuthError(ApiError):
    """密钥或设备配置错误，继续重试没有意义。"""


class ApiClient:
    def __init__(self, base_url: str, service_key: str, *, timeout: float = 10.0) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-AI-Service-Key": service_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def close(self) -> None:
        self._session.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        url = f"{self._base}{path}"
        response = self._session.request(method, url, timeout=self._timeout, **kwargs)
        try:
            body = response.json()
        except ValueError:
            body = {"message": response.text[:200]}
        if response.status_code in (401, 403):
            raise AuthError(response.status_code, str(body.get("message", "认证失败")))
        if response.status_code != 200:
            raise ApiError(response.status_code, str(body.get("message", "请求失败")))
        data = body.get("data")
        if not isinstance(data, dict):
            raise ApiError(response.status_code, "响应缺少 data 字段")
        return data

    def context(self, session_id: int, device_id: str) -> dict:
        return self._request(
            "GET",
            "/api/v1/ai/context",
            params={"session_id": session_id, "device_id": device_id},
        )

    def upload(self, payload: dict) -> dict:
        return self._request("POST", "/api/v1/ai/emoji-results", json=payload)
