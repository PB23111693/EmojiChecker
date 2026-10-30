"""端到端用例：管理员排课、学生提交、教师看板、管理员统计与导出。"""

from __future__ import annotations

import datetime as dt
import uuid

from tests.conftest import auth_headers


def _iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat()


def test_full_flow_admin_student_teacher_admin(client, seed):
    """E2E01 管理员建课排人 → 学生提交 → 教师看板 → 管理员统计与导出。"""
    admin = auth_headers(client, "admin")
    now = dt.datetime.now(dt.timezone.utc)

    course = client.post(
        "/api/v1/admin/courses",
        json={"name": "端到端课程", "teacher_id": seed["teacher_id"]},
        headers=admin,
    )
    assert course.status_code == 201
    course_id = course.json()["data"]["id"]

    session = client.post(
        "/api/v1/admin/sessions",
        json={
            "course_id": course_id,
            "class_name": "计科２１０１",
            "room": "A101",
            "start_at": _iso(now + dt.timedelta(minutes=10)),
            "end_at": _iso(now + dt.timedelta(minutes=70)),
            "ai_threshold": 0.6,
        },
        headers=admin,
    )
    assert session.status_code == 201
    session_id = session.json()["data"]["id"]
    assert session.json()["data"]["class_name"] == "计科2101"

    members = client.put(
        f"/api/v1/admin/sessions/{session_id}/members",
        json={"user_ids": [seed["student_ids"][0]]},
        headers=admin,
    )
    assert members.status_code == 200

    # 演示与测试使用同一流程：名单保存后把开始时间前移，课堂立即进入进行中。
    opened = client.patch(
        f"/api/v1/admin/sessions/{session_id}",
        json={
            "start_at": _iso(now - dt.timedelta(minutes=1)),
            "end_at": _iso(now + dt.timedelta(minutes=30)),
        },
        headers=admin,
    )
    assert opened.status_code == 200
    assert opened.json()["data"]["status"] == "ONGOING"

    student = auth_headers(client, "stu1")
    submitted = client.post(
        "/api/v1/emoji",
        json={"event_id": uuid.uuid4().hex, "session_id": session_id, "emotion": "HAPPY"},
        headers=student,
    )
    assert submitted.status_code == 200

    teacher = auth_headers(client, "teacher_a")
    dashboard = client.get(
        f"/api/v1/dashboard/realtime?session_id={session_id}", headers=teacher
    )
    assert dashboard.status_code == 200
    block = dashboard.json()["data"]["manual"]
    assert block["total"] == 1
    assert block["participants"] == 1
    assert block["member_count"] == 1
    assert block["coverage"] == 1.0

    statistics = client.get(
        f"/api/v1/statistics?course_id={course_id}", headers=admin
    )
    assert statistics.status_code == 200
    assert statistics.json()["data"]["total"] == 1

    exported = client.get(
        f"/api/v1/admin/emoji/export?course_id={course_id}", headers=admin
    )
    assert exported.status_code == 200
    assert exported.content.startswith(b"\xef\xbb\xbf")
    assert exported.headers["X-Export-Rows"] == "1"

    other_teacher = auth_headers(client, "teacher_b")
    denied = client.get(
        f"/api/v1/dashboard/realtime?session_id={session_id}", headers=other_teacher
    )
    assert denied.status_code == 404
