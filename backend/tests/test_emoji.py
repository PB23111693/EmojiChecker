"""手动反馈用例。对应 AT03、AT04、AT05、AT06。"""

from __future__ import annotations

import datetime as dt
import uuid

from app.core.config import settings
from tests.conftest import auth_headers


def _event_id() -> str:
    return uuid.uuid4().hex


def test_submit_and_query_history(client, seed):
    """AT03 名单内学生提交成功，个人历史只包含本人记录。"""
    headers = auth_headers(client, "stu1")
    event_id = _event_id()
    response = client.post(
        "/api/v1/emoji",
        json={"event_id": event_id, "session_id": seed["ongoing_id"], "emotion": "HAPPY"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["duplicate"] is False
    assert data["record_id"] > 0

    history = client.get("/api/v1/emoji/history", headers=headers)
    assert history.status_code == 200
    body = history.json()["data"]
    assert body["total"] == 1
    assert body["items"][0]["emotion"] == "HAPPY"
    assert body["items"][0]["source"] == "MANUAL"


def test_submit_requires_membership(client, seed):
    """AT04 未排入名单的学生不能提交。"""
    headers = auth_headers(client, "stu1")
    response = client.post(
        "/api/v1/emoji",
        json={"event_id": _event_id(), "session_id": seed["foreign_id"], "emotion": "HAPPY"},
        headers=headers,
    )
    assert response.status_code == 403


def test_submit_rejected_outside_window(client, seed, db):
    """AT04 未开始与已结束的课堂均明确拒绝。"""
    from app.models import ScheduleUser

    for session_key in ("pending_id", "ended_id"):
        db.add(ScheduleUser(session_id=seed[session_key], user_id=seed["student_ids"][0]))
    db.commit()

    headers = auth_headers(client, "stu1")
    for session_key in ("pending_id", "ended_id"):
        response = client.post(
            "/api/v1/emoji",
            json={"event_id": _event_id(), "session_id": seed[session_key], "emotion": "SAD"},
            headers=headers,
        )
        assert response.status_code == 409, session_key


def test_duplicate_event_returns_same_record(client, seed):
    """AT06 同一 event_id 重试返回原记录，不新增数据。"""
    headers = auth_headers(client, "stu1")
    event_id = _event_id()
    payload = {"event_id": event_id, "session_id": seed["ongoing_id"], "emotion": "NEUTRAL"}

    first = client.post("/api/v1/emoji", json=payload, headers=headers)
    second = client.post("/api/v1/emoji", json=payload, headers=headers)
    assert second.status_code == 200
    assert second.json()["data"]["duplicate"] is True
    assert second.json()["data"]["record_id"] == first.json()["data"]["record_id"]

    history = client.get("/api/v1/emoji/history", headers=headers)
    assert history.json()["data"]["total"] == 1


def test_event_id_conflict_with_different_emotion(client, seed):
    headers = auth_headers(client, "stu1")
    event_id = _event_id()
    client.post(
        "/api/v1/emoji",
        json={"event_id": event_id, "session_id": seed["ongoing_id"], "emotion": "HAPPY"},
        headers=headers,
    )
    conflict = client.post(
        "/api/v1/emoji",
        json={"event_id": event_id, "session_id": seed["ongoing_id"], "emotion": "ANGRY"},
        headers=headers,
    )
    assert conflict.status_code == 409


def test_manual_slot_limits_repeated_submission(client, seed):
    """AT06 同一时间片内第二次提交被拒绝。"""
    previous = settings.manual_slot_seconds
    object.__setattr__(settings, "manual_slot_seconds", 30)
    try:
        headers = auth_headers(client, "stu1")
        first = client.post(
            "/api/v1/emoji",
            json={
                "event_id": _event_id(),
                "session_id": seed["ongoing_id"],
                "emotion": "HAPPY",
            },
            headers=headers,
        )
        assert first.status_code == 200
        second = client.post(
            "/api/v1/emoji",
            json={
                "event_id": _event_id(),
                "session_id": seed["ongoing_id"],
                "emotion": "SAD",
            },
            headers=headers,
        )
        assert second.status_code == 409
        assert "30" in second.json()["message"]
    finally:
        object.__setattr__(settings, "manual_slot_seconds", previous)


def test_student_history_is_scoped_to_self(client, seed):
    """AT05 学生无法通过 user_id 参数查看他人记录。"""
    stu1 = auth_headers(client, "stu1")
    stu2 = auth_headers(client, "stu2")
    client.post(
        "/api/v1/emoji",
        json={"event_id": _event_id(), "session_id": seed["ongoing_id"], "emotion": "HAPPY"},
        headers=stu1,
    )

    leaked = client.get(
        f"/api/v1/emoji/history?user_id={seed['student_ids'][0]}", headers=stu2
    )
    assert leaked.status_code == 200
    assert leaked.json()["data"]["total"] == 0


def test_teacher_history_scoped_to_own_course(client, seed):
    teacher = auth_headers(client, "teacher_a")
    other = auth_headers(client, "teacher_b")
    client.post(
        "/api/v1/emoji",
        json={"event_id": _event_id(), "session_id": seed["ongoing_id"], "emotion": "HAPPY"},
        headers=auth_headers(client, "stu1"),
    )

    visible = client.get("/api/v1/emoji/history", headers=teacher)
    assert visible.json()["data"]["total"] == 1

    hidden = client.get("/api/v1/emoji/history", headers=other)
    assert hidden.json()["data"]["total"] == 0


def test_teacher_can_list_session_students(client, seed):
    client.post(
        "/api/v1/emoji",
        json={"event_id": _event_id(), "session_id": seed["ongoing_id"], "emotion": "SURPRISED"},
        headers=auth_headers(client, "stu1"),
    )
    response = client.get(
        f"/api/v1/sessions/{seed['ongoing_id']}/students",
        headers=auth_headers(client, "teacher_a"),
    )
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["username"] == "stu1"
    assert items[0]["record_count"] == 1


def test_retry_after_session_end_returns_original(client, seed, db):
    """AT06/B04 课堂结束后原样重试已成功事件，仍返回原记录而非拒绝。"""
    from app.db.base import utcnow
    from app.models import ClassSession

    headers = auth_headers(client, "stu1")
    event_id = _event_id()
    payload = {"event_id": event_id, "session_id": seed["ongoing_id"], "emotion": "HAPPY"}
    first = client.post("/api/v1/emoji", json=payload, headers=headers)
    assert first.status_code == 200

    session = db.get(ClassSession, seed["ongoing_id"])
    session.end_at = utcnow() - dt.timedelta(minutes=1)
    db.commit()

    retry = client.post("/api/v1/emoji", json=payload, headers=headers)
    assert retry.status_code == 200, retry.text
    assert retry.json()["data"]["duplicate"] is True
    assert retry.json()["data"]["record_id"] == first.json()["data"]["record_id"]
