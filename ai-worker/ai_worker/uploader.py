"""批量上传、有限退避重试与丢弃计数。

规则与设计方案 8.3 一致：只重试传输失败或 5xx；401/403 立即停止；
请求级 422 整批丢弃；HTTP 200 的逐事件拒绝只丢弃对应事件。
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field

import requests

from ai_worker.api import ApiClient, ApiError, AuthError
from ai_worker.filter import EmotionEvent

logger = logging.getLogger(__name__)

RETRY_DELAYS = (1, 2, 4, 8)
MAX_QUEUE = 100
MAX_EVENT_AGE_SECONDS = 30
BATCH_SIZE = 100


@dataclass
class UploadStats:
    accepted: int = 0
    duplicates: int = 0
    rejected: int = 0
    expired: int = 0
    overflow: int = 0
    batch_failed: int = 0
    retry_failures: int = 0

    def summary(self) -> str:
        return (
            f"accepted={self.accepted} duplicates={self.duplicates} "
            f"rejected={self.rejected} expired={self.expired} "
            f"overflow={self.overflow} batch_failed={self.batch_failed} "
            f"retry_failures={self.retry_failures}"
        )


@dataclass
class _Item:
    event: EmotionEvent
    enqueued_at: float = field(default_factory=time.monotonic)


class Uploader:
    def __init__(
        self,
        api: ApiClient,
        *,
        session_id: int,
        device_id: str,
        model_version: str,
        max_queue: int = MAX_QUEUE,
        max_age_seconds: int = MAX_EVENT_AGE_SECONDS,
        batch_size: int = BATCH_SIZE,
    ) -> None:
        self._api = api
        self._session_id = session_id
        self._device_id = device_id
        self._model_version = model_version
        self._max_queue = max_queue
        self._max_age = max_age_seconds
        self._batch_size = batch_size
        self._queue: deque[_Item] = deque()
        self.stats = UploadStats()

    @property
    def pending(self) -> int:
        return len(self._queue)

    def enqueue(self, events: list[EmotionEvent]) -> None:
        for event in events:
            if len(self._queue) >= self._max_queue:
                self._queue.popleft()
                self.stats.overflow += 1
                logger.warning("上传队列已满，丢弃最旧事件")
            self._queue.append(_Item(event=event))

    def _drop_expired(self) -> None:
        now = time.monotonic()
        while self._queue and now - self._queue[0].enqueued_at > self._max_age:
            self._queue.popleft()
            self.stats.expired += 1
            logger.warning("事件超过 %s 秒未送达，已丢弃", self._max_age)

    def _payload(self, items: list[_Item]) -> dict:
        return {
            "device_id": self._device_id,
            "session_id": self._session_id,
            "model_version": self._model_version,
            "results": [
                {
                    "event_id": item.event.event_id,
                    "observed_at": item.event.observed_at.isoformat(),
                    "emotion": item.event.emotion,
                    "confidence": item.event.confidence,
                }
                for item in items
            ],
        }

    def flush(self) -> UploadStats:
        """发送当前队列。成功、逐事件拒绝或整批 422 都会从队列移除。"""
        self._drop_expired()
        while self._queue:
            batch = [self._queue.popleft() for _ in range(min(self._batch_size, len(self._queue)))]
            if not self._send(batch):
                # 批次已放回队列，等待下一次采样再试，避免在失败时忙等。
                break
        return self.stats

    def _prune(self, batch: list[_Item]) -> list[_Item]:
        """重试前再次检查事件年龄，保证单事件不超过保留上限。"""
        now = time.monotonic()
        alive: list[_Item] = []
        for item in batch:
            if now - item.enqueued_at > self._max_age:
                self.stats.expired += 1
                logger.warning("事件超过 %s 秒未送达，已丢弃", self._max_age)
            else:
                alive.append(item)
        return alive

    def _send(self, batch: list[_Item]) -> bool:
        """返回 True 表示批次已从队列移除，False 表示已放回队列等待重试。"""
        for delay in RETRY_DELAYS:
            # 每次重试前重新计算年龄；超时或退避耗时可能使事件超过 30 秒。
            batch = self._prune(batch)
            if not batch:
                return True
            payload = self._payload(batch)
            try:
                data = self._api.upload(payload)
            except AuthError:
                # 凭据错误不可重试；把事件放回队列，由调用方停止进程。
                self._restore(batch)
                raise
            except ApiError as exc:
                if exc.status_code == 422:
                    self.stats.batch_failed += len(batch)
                    logger.error("批次校验失败，整批丢弃：%s", exc.message)
                    return True
                if exc.status_code >= 500:
                    logger.warning("后端 %s，%s 秒后重试", exc.status_code, delay)
                    time.sleep(delay)
                    continue
                self._restore(batch)
                raise
            except requests.RequestException as exc:
                logger.warning("上传失败（%s），%s 秒后重试", exc.__class__.__name__, delay)
                time.sleep(delay)
                continue
            else:
                self._record(data)
                return True

        self.stats.retry_failures += len(batch)
        logger.error("连续 %s 次上传失败，事件保留在队列等待下次采样", len(RETRY_DELAYS))
        self._restore(batch)
        return False

    def _record(self, data: dict) -> None:
        self.stats.accepted += int(data.get("accepted", 0))
        self.stats.duplicates += int(data.get("duplicates", 0))
        self.stats.rejected += int(data.get("rejected", 0))
        for detail in data.get("details", []):
            if detail.get("status") == "REJECTED":
                logger.warning(
                    "事件 %s 被拒绝：%s", detail.get("event_id"), detail.get("reason")
                )

    def _restore(self, batch: list[_Item]) -> None:
        for item in reversed(batch):
            if time.monotonic() - item.enqueued_at <= self._max_age:
                self._queue.appendleft(item)
            else:
                self.stats.expired += 1
