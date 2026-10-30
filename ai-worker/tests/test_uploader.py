"""上传队列、重试与整批丢弃用例。"""

from __future__ import annotations

import datetime as dt

import pytest
import requests

from ai_worker.api import ApiError, AuthError
from ai_worker.filter import EmotionEvent
from ai_worker import uploader as uploader_module
from ai_worker.uploader import Uploader


class FakeApi:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def upload(self, payload: dict) -> dict:
        self.calls.append(payload)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _event(emotion: str = "HAPPY") -> EmotionEvent:
    return EmotionEvent(
        event_id="a" * 32,
        observed_at=dt.datetime.now(dt.timezone.utc),
        emotion=emotion,
        confidence=0.8,
    )


def _uploader(api: FakeApi) -> Uploader:
    return Uploader(
        api,  # type: ignore[arg-type]
        session_id=1,
        device_id="test-device",
        model_version="test-model",
    )


def test_success_records_counts(monkeypatch):
    """AT11 批量成功后按逐事件结果计数，队列清空。"""
    api = FakeApi(
        [
            {
                "accepted": 1,
                "duplicates": 0,
                "rejected": 1,
                "details": [{"event_id": "a" * 32, "status": "REJECTED", "reason": "BELOW_THRESHOLD"}],
            }
        ]
    )
    uploader = _uploader(api)
    uploader.enqueue([_event(), _event("SAD")])
    stats = uploader.flush()
    assert stats.accepted == 1
    assert stats.rejected == 1
    assert uploader.pending == 0
    assert api.calls[0]["session_id"] == 1


def test_retries_transport_error(monkeypatch):
    """AT12 网络失败按退避重试，成功后不重复入队。"""
    monkeypatch.setattr(uploader_module, "RETRY_DELAYS", (0, 0, 0, 0))
    monkeypatch.setattr(uploader_module.time, "sleep", lambda _: None)
    api = FakeApi(
        [
            requests.ConnectionError("boom"),
            requests.Timeout("timeout"),
            {"accepted": 1, "duplicates": 0, "rejected": 0, "details": []},
        ]
    )
    uploader = _uploader(api)
    uploader.enqueue([_event()])
    stats = uploader.flush()
    assert stats.accepted == 1
    assert len(api.calls) == 3
    assert uploader.pending == 0


def test_validation_error_drops_batch(monkeypatch):
    """AT16 请求级 422 整批丢弃，不重试。"""
    api = FakeApi([ApiError(422, "请求参数不合法")])
    uploader = _uploader(api)
    uploader.enqueue([_event()])
    stats = uploader.flush()
    assert stats.batch_failed == 1
    assert uploader.pending == 0
    assert len(api.calls) == 1


def test_auth_error_stops_and_restores(monkeypatch):
    """AT11 密钥错误立即停止，事件放回队列。"""
    api = FakeApi([AuthError(401, "AI 服务密钥无效")])
    uploader = _uploader(api)
    uploader.enqueue([_event()])
    with pytest.raises(AuthError):
        uploader.flush()
    assert uploader.pending == 1


def test_queue_overflow_drops_oldest():
    """AT12 队列超过上限时丢弃最旧事件并计数。"""
    api = FakeApi([])
    uploader = Uploader(
        api,  # type: ignore[arg-type]
        session_id=1,
        device_id="test-device",
        model_version="test-model",
        max_queue=2,
    )
    uploader.enqueue([_event(), _event(), _event()])
    assert uploader.pending == 2
    assert uploader.stats.overflow == 1


def test_retry_prunes_events_exceeding_age(monkeypatch):
    """A04 每次重试前重新检查事件年龄，超过 30 秒不再发送。"""
    clock = [0.0]
    monkeypatch.setattr(uploader_module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(uploader_module.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    monkeypatch.setattr(uploader_module, "RETRY_DELAYS", (1, 2, 4, 8))

    class TimeoutApi:
        def __init__(self) -> None:
            self.calls = 0

        def upload(self, _payload):
            self.calls += 1
            clock[0] += 10
            raise requests.Timeout("slow")

    api = TimeoutApi()
    uploader = _uploader(api)  # type: ignore[arg-type]
    uploader.enqueue([_event()])
    # _Item 的 default_factory 在类定义时绑定了原始函数，测试中显式对齐虚拟时钟。
    uploader._queue[0].enqueued_at = 0.0
    stats = uploader.flush()

    assert api.calls == 3
    assert stats.expired == 1
    assert uploader.pending == 0
