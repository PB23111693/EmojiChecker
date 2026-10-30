"""轻量限流。单进程内存实现，仅对登录与提交接口生效。

多进程部署时每个进程独立计数，生产环境应替换为 Redis 实现，此限制记录在部署说明中。
"""

from __future__ import annotations

import threading
import time
from collections import deque

from app.core.errors import RateLimited


class SlidingWindowLimiter:
    def __init__(self, *, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits.setdefault(key, deque())
            while bucket and now - bucket[0] > self.window:
                bucket.popleft()
            if len(bucket) >= self.limit:
                raise RateLimited()
            bucket.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


login_limiter = SlidingWindowLimiter(limit=120)
emoji_limiter = SlidingWindowLimiter(limit=120)
