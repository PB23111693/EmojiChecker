"""AI 入库用例。对应 AT09、AT10、AT11、AT12、AT16。"""

from __future__ import annotations

import datetime as dt
import uuid

from tests.conftest import auth_headers

AI_HEADERS = {"X-AI-Service-Key": "test-ai-key"}


def _payload(session_id: int, **overrides) -> dict:
    now = dt.datetime.now(dt.timezone.utc)
    item = {
        "event_id": uuid.uuid4().hex,
        "observed_at": (now - dt.timedelta(seconds=5)).isoformat(),
        "emotion": "HAPPY",
        "confidence": 0.92,
    }
    item.update(overrides)
    return {
        "device_id": "test-device",
        "session_id": session_id,
        "model_version": "fer-onnx-1.0",
        "results": [item],
    }


def test_ingest_creates_anonymous_record(client, seed):
    """AT09 真摄像头事件可入库，用户为空，来源为 AI。"""
    response = client.post(
        "/api/v1/ai/emoji-results", json=_payload(seed["ongoing_id"]), headers=AI_HEADERS
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["accepted"] == 1
    assert data["rejected"] == 0

    dashboard = client.get(
        f"/api/v1/dashboard/realtime?session_id={seed['ongoing_id']}",
        headers=auth_headers(client, "teacher_a"),
    )
    body = dashboard.json()["data"]
    assert body["ai"]["total"] == 1
    assert body["manual"]["total"] == 0


def test_ingest_is_idempotent(client, seed):
    """AT11 同一事件重复上传只入库一次，内容不一致返回冲突。"""
    payload = _payload(seed["ongoing_id"])
    first = client.post("/api/v1/ai/emoji-results", json=payload, headers=AI_HEADERS)
    assert first.json()["data"]["accepted"] == 1

    second = client.post("/api/v1/ai/emoji-results", json=payload, headers=AI_HEADERS)
    assert second.json()["data"]["duplicates"] == 1
    assert second.json()["data"]["accepted"] == 0

    conflicting = _payload(seed["ongoing_id"])
    conflicting["results"][0]["event_id"] = payload["results"][0]["event_id"]
    response = client.post("/api/v1/ai/emoji-results", json=conflicting, headers=AI_HEADERS)
    assert response.json()["data"]["rejected"] == 1
    assert response.json()["data"]["details"][0]["reason"] == "EVENT_ID_CONFLICT"


def test_below_threshold_rejected(client, seed):
    """AT10 低于课堂阈值的分类结果丢弃，不生成假数据。"""
    response = client.post(
        "/api/v1/ai/emoji-results",
        json=_payload(seed["ongoing_id"], confidence=0.59),
        headers=AI_HEADERS,
    )
    data = response.json()["data"]
    assert data["accepted"] == 0
    assert data["rejected"] == 1
    assert data["details"][0]["reason"] == "BELOW_THRESHOLD"

    threshold_equal = client.post(
        "/api/v1/ai/emoji-results",
        json=_payload(seed["ongoing_id"], confidence=0.6),
        headers=AI_HEADERS,
    )
    assert threshold_equal.json()["data"]["accepted"] == 1


def test_invalid_batch_rejected_as_whole(client, seed):
    """AT16 非法字段整批 422，且零写入。"""
    payload = _payload(seed["ongoing_id"], confidence=1.5)
    response = client.post("/api/v1/ai/emoji-results", json=payload, headers=AI_HEADERS)
    assert response.status_code == 422

    dashboard = client.get(
        f"/api/v1/dashboard/realtime?session_id={seed['ongoing_id']}",
        headers=auth_headers(client, "teacher_a"),
    )
    assert dashboard.json()["data"]["ai"]["total"] == 0


def test_ai_endpoint_rejects_user_token_and_wrong_key(client, seed):
    """AT11 用户令牌不能调用 AI 接口，错误密钥无写入。"""
    token_headers = auth_headers(client, "admin")
    no_key = client.post(
        "/api/v1/ai/emoji-results", json=_payload(seed["ongoing_id"]), headers=token_headers
    )
    assert no_key.status_code == 401

    wrong_key = client.post(
        "/api/v1/ai/emoji-results",
        json=_payload(seed["ongoing_id"]),
        headers={"X-AI-Service-Key": "wrong-key"},
    )
    assert wrong_key.status_code == 401

    wrong_device = client.post(
        "/api/v1/ai/emoji-results",
        json={**_payload(seed["ongoing_id"]), "device_id": "other-device"},
        headers=AI_HEADERS,
    )
    assert wrong_device.status_code == 403


def test_session_ended_rejects_new_but_confirms_duplicates(client, seed):
    """AT12 课堂结束后新事件拒收，已成功事件重试仍返回原确认。"""
    payload = _payload(seed["ongoing_id"])
    client.post("/api/v1/ai/emoji-results", json=payload, headers=AI_HEADERS)

    response = client.post(
        "/api/v1/ai/emoji-results", json=_payload(seed["ended_id"]), headers=AI_HEADERS
    )
    data = response.json()["data"]
    assert data["accepted"] == 0
    assert data["details"][0]["reason"] == "SESSION_NOT_ONGOING"

    retry = client.post("/api/v1/ai/emoji-results", json=payload, headers=AI_HEADERS)
    assert retry.json()["data"]["duplicates"] == 1


def test_ai_context_returns_threshold(client, seed):
    response = client.get(
        f"/api/v1/ai/context?session_id={seed['ongoing_id']}&device_id=test-device",
        headers=AI_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["ai_threshold"] == 0.6
    assert data["status"] == "ONGOING"
    assert len(data["emotions"]) == 7


def test_context_rejects_wrong_device(client, seed):
    """AT11 设备标识与服务密钥绑定的设备不一致时拒绝取配置。"""
    response = client.get(
        "/api/v1/ai/context",
        params={"session_id": seed["ongoing_id"], "device_id": "other-device"},
        headers=AI_HEADERS,
    )
    assert response.status_code == 403
