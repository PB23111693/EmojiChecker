"""实时看板广播。WebSocket 只推送变更信号，不承载业务数据。"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class RealtimeHub:
    def __init__(self) -> None:
        self._channels: dict[int, set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def publish_nowait(self, session_id: int, payload: dict[str, Any]) -> None:
        """供同步接口调用，把广播调度回事件循环线程。"""
        if self._loop is None or self._loop.is_closed():
            return
        self._loop.call_soon_threadsafe(
            lambda: asyncio.create_task(self.publish(session_id, payload))
        )

    async def subscribe(self, session_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            self._channels.setdefault(session_id, set()).add(websocket)

    async def unsubscribe(self, session_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._channels.get(session_id)
            if not connections:
                return
            connections.discard(websocket)
            if not connections:
                self._channels.pop(session_id, None)

    async def publish(self, session_id: int, payload: dict[str, Any]) -> int:
        connections = list(self._channels.get(session_id, ()))
        if not connections:
            return 0
        message = json.dumps(payload, ensure_ascii=False)
        stale: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_text(message)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            await self.unsubscribe(session_id, websocket)
        return len(connections) - len(stale)

    def connection_count(self, session_id: int) -> int:
        return len(self._channels.get(session_id, ()))


hub = RealtimeHub()
