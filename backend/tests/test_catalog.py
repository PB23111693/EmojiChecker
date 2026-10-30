"""课程、课堂与名单用例。对应 AT02、AT04 与 AT15 的名单分支。"""

from __future__ import annotations

import datetime as dt

from tests.conftest import auth_headers


def _iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat()


def test_create_course_and_session(client, seed):
    """AT02 管理员创建课程与课堂，教师与时间正确。"""
    headers = auth_headers(client, "admin")
    course = client.post(
        "/api/v1/admin/courses",
        json={"name": "操作系统", "teacher_id": seed["teacher_id"]},
        headers=headers,
    )
    assert course.status_code == 201
    course_id = course.json()["data"]["id"]

    now = dt.datetime.now(dt.timezone.utc)
    created = client.post(
        "/api/v1/admin/sessions",
        json={
            "course_id": course_id,
            "class_name": "计科2103",
            "room": "C301",
            "start_at": _iso(now + dt.timedelta(hours=1)),
            "end_at": _iso(now + dt.timedelta(hours=2)),
            "ai_threshold": 0.55,
        },
        headers=headers,
    )
    assert created.status_code == 201
    data = created.json()["data"]
    assert data["status"] == "PENDING"
    assert data["teacher_name"] == "teacher_a"
    assert data["ai_threshold"] == 0.55


def test_session_time_window_validation(client, seed):
    headers = auth_headers(client, "admin")
    now = dt.datetime.now(dt.timezone.utc)
    response = client.post(
        "/api/v1/admin/sessions",
        json={
            "course_id": seed["course_id"],
            "class_name": "计科2103",
            "start_at": _iso(now + dt.timedelta(hours=2)),
            "end_at": _iso(now + dt.timedelta(hours=1)),
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_schedule_members_deduplicated(client, seed):
    """AT02 重复保存名单不产生重复成员，非学生不能加入。"""
    headers = auth_headers(client, "admin")
    ids = seed["student_ids"]
    payload = {"user_ids": [ids[0], ids[1], ids[0]]}
    response = client.put(
        f"/api/v1/admin/sessions/{seed['pending_id']}/members", json=payload, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["data"]["member_count"] == 2

    again = client.put(
        f"/api/v1/admin/sessions/{seed['pending_id']}/members", json=payload, headers=headers
    )
    assert again.json()["data"]["member_count"] == 2

    bad = client.put(
        f"/api/v1/admin/sessions/{seed['pending_id']}/members",
        json={"user_ids": [seed["teacher_id"]]},
        headers=headers,
    )
    assert bad.status_code == 422


def test_members_frozen_after_start(client, seed):
    headers = auth_headers(client, "admin")
    response = client.put(
        f"/api/v1/admin/sessions/{seed['ongoing_id']}/members",
        json={"user_ids": []},
        headers=headers,
    )
    assert response.status_code == 409


def test_session_update_frozen_after_start(client, seed):
    headers = auth_headers(client, "admin")
    response = client.patch(
        f"/api/v1/admin/sessions/{seed['ongoing_id']}",
        json={"ai_threshold": 0.9},
        headers=headers,
    )
    assert response.status_code == 409


def test_session_cancel_before_start(client, seed):
    headers = auth_headers(client, "admin")
    response = client.patch(
        f"/api/v1/admin/sessions/{seed['pending_id']}",
        json={"cancelled": True},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "CANCELLED"


def test_role_based_session_visibility(client, seed):
    """AT05 教师只能看到所授课程，学生只能看到被安排的课堂。"""
    teacher_headers = auth_headers(client, "teacher_a")
    other_headers = auth_headers(client, "teacher_b")
    student_headers = auth_headers(client, "stu1")

    teacher_sessions = client.get("/api/v1/sessions?page_size=50", headers=teacher_headers)
    assert teacher_sessions.status_code == 200
    ids = {item["id"] for item in teacher_sessions.json()["data"]["items"]}
    assert seed["foreign_id"] not in ids

    forbidden = client.get(f"/api/v1/sessions/{seed['foreign_id']}", headers=other_headers)
    assert forbidden.status_code == 200

    denied = client.get(
        f"/api/v1/sessions/{seed['foreign_id']}", headers=teacher_headers
    )
    assert denied.status_code == 404

    student_sessions = client.get("/api/v1/sessions?page_size=50", headers=student_headers)
    student_ids = {item["id"] for item in student_sessions.json()["data"]["items"]}
    assert student_ids == {seed["ongoing_id"]}


def test_student_cannot_create_course(client, seed):
    headers = auth_headers(client, "stu1")
    response = client.post(
        "/api/v1/admin/courses",
        json={"name": "越权课程", "teacher_id": seed["teacher_id"]},
        headers=headers,
    )
    assert response.status_code == 403


def test_class_name_normalized_and_schedule_alias(client, seed):
    """AT02 班级名全角半角归一；指导书示例路径的兼容别名可用。"""
    headers = auth_headers(client, "admin")
    now = dt.datetime.now(dt.timezone.utc)
    created = client.post(
        "/api/v1/admin/sessions",
        json={
            "course_id": seed["course_id"],
            "class_name": "计科　２１０３",
            "start_at": _iso(now + dt.timedelta(hours=3)),
            "end_at": _iso(now + dt.timedelta(hours=4)),
        },
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["data"]["class_name"] == "计科 2103"

    queried = client.get(
        "/api/v1/sessions", params={"class_name": "计科 2103"}, headers=headers
    )
    assert queried.status_code == 200
    assert any(item["class_name"] == "计科 2103" for item in queried.json()["data"]["items"])

    session_id = created.json()["data"]["id"]
    scheduled = client.post(
        f"/api/v1/admin/sessions/{session_id}/schedule",
        json={"user_ids": seed["student_ids"][:2]},
        headers=headers,
    )
    assert scheduled.status_code == 200
    assert scheduled.json()["data"]["member_count"] == 2


def test_patch_naive_datetime_returns_422(client, seed):
    """B01 更新课堂时缺少时区偏移量应返回 422，而不是 500。"""
    headers = auth_headers(client, "admin")
    response = client.patch(
        f"/api/v1/admin/sessions/{seed['pending_id']}",
        json={"start_at": "2026-11-01T12:00:00"},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["code"] == 42200


def test_student_cannot_read_all_classes_or_members(client, seed):
    """B03 学生不能读取全站班级列表或全班名单。"""
    headers = auth_headers(client, "stu1")
    assert client.get("/api/v1/admin/classes", headers=headers).status_code == 403
    assert (
        client.get(
            f"/api/v1/admin/sessions/{seed['ongoing_id']}/members", headers=headers
        ).status_code
        == 403
    )
