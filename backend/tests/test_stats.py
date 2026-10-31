"""统计、看板与导出用例。对应 AT07、AT08、AT13。"""

from __future__ import annotations

import datetime as dt
import uuid

from app.db.base import utcnow
from app.models import ClassSession, EmojiRecord, Source, Emotion
from tests.conftest import auth_headers


def _submit(client, seed, username: str, emotion: str) -> None:
    response = client.post(
        "/api/v1/emoji",
        json={
            "event_id": uuid.uuid4().hex,
            "session_id": seed["ongoing_id"],
            "emotion": emotion,
        },
        headers=auth_headers(client, username),
    )
    assert response.status_code == 200, response.text


def test_dashboard_separates_manual_and_ai(client, seed):
    """AT07 手动次数、参与人数与 AI 观察次数分别计算。"""
    _submit(client, seed, "stu1", "HAPPY")
    _submit(client, seed, "stu2", "HAPPY")
    _submit(client, seed, "stu2", "SAD")

    now = utcnow()
    db = client.app.state  # 占位，实际通过下面的 fixture 访问
    del db

    response = client.get(
        f"/api/v1/dashboard/realtime?session_id={seed['ongoing_id']}",
        headers=auth_headers(client, "teacher_a"),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["manual"]["total"] == 3
    assert data["manual"]["participants"] == 2
    assert data["manual"]["member_count"] == 3
    assert data["manual"]["coverage"] == round(2 / 3, 4)
    assert data["ai"]["total"] == 0
    assert data["manual"]["distribution"][0]["emotion"] == "HAPPY"
    assert data["trend"]
    assert now.tzinfo is not None


def test_statistics_filters_and_empty_state(client, seed):
    """AT13 空筛选结果不报错，计数为零。"""
    response = client.get(
        f"/api/v1/statistics?course_id={seed['course_id']}&source=AI",
        headers=auth_headers(client, "admin"),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 0
    assert data["distribution"] == []
    assert data["participants"] == 0


def test_export_csv_blocks_formula_injection(client, seed, db):
    """AT08 导出含中文与公式前缀的字段，Excel 打开不执行公式。"""
    session = db.get(ClassSession, seed["ongoing_id"])
    session.class_name = '=HYPERLINK("http://evil.example","点我")'
    db.add(
        EmojiRecord(
            event_id=uuid.uuid4().hex,
            session_id=session.id,
            user_id=seed["student_ids"][0],
            emotion=Emotion.HAPPY,
            source=Source.MANUAL,
            observed_at=utcnow(),
            received_at=utcnow(),
            manual_slot=None,
        )
    )
    db.commit()

    response = client.get(
        f"/api/v1/admin/emoji/export?session_id={seed['ongoing_id']}",
        headers=auth_headers(client, "admin"),
    )
    assert response.status_code == 200
    assert response.content.startswith(b"\xef\xbb\xbf")
    text = response.content.decode("utf-8-sig")
    assert "记录ID" in text
    assert "'=HYPERLINK" in text


def test_export_requires_admin(client, seed):
    response = client.get(
        "/api/v1/admin/emoji/export",
        headers=auth_headers(client, "teacher_a"),
    )
    assert response.status_code == 403


def test_student_cannot_read_statistics(client, seed):
    response = client.get("/api/v1/statistics", headers=auth_headers(client, "stu1"))
    assert response.status_code == 404


def test_trend_bucket_boundaries(client, seed, db):
    """AT07 分钟趋势按观测时间分桶，左闭右开。"""
    base = dt.datetime(2026, 10, 29, 2, 0, tzinfo=dt.timezone.utc)
    for offset in (0, 30, 61):
        db.add(
            EmojiRecord(
                event_id=uuid.uuid4().hex,
                session_id=seed["ongoing_id"],
                user_id=seed["student_ids"][0],
                emotion=Emotion.NEUTRAL,
                source=Source.MANUAL,
                observed_at=base + dt.timedelta(seconds=offset),
                received_at=base + dt.timedelta(seconds=offset),
                manual_slot=None,
            )
        )
    db.commit()

    response = client.get(
        f"/api/v1/statistics?session_id={seed['ongoing_id']}&source=MANUAL",
        headers=auth_headers(client, "teacher_a"),
    )
    assert response.status_code == 200
    trend = response.json()["data"]["trend"]
    assert len(trend) == 2
    assert trend[0]["manual"] == 2
    assert trend[1]["manual"] == 1


def test_compat_paths(client, seed):
    """AT07 指导书示例路径的兼容别名返回同一口径。"""
    teacher = auth_headers(client, "teacher_a")
    admin = auth_headers(client, "admin")

    dashboard = client.get(
        f"/api/v1/admin/dashboard/realtime?session_id={seed['ongoing_id']}", headers=teacher
    )
    assert dashboard.status_code == 200
    assert "manual" in dashboard.json()["data"]

    assert client.get("/api/v1/admin/statistics", headers=admin).status_code == 200
    assert client.get("/api/v1/emoji/statistics", headers=admin).status_code == 200


def test_participants_respects_user_and_source_filters(client, seed):
    """B02 按学生筛选时参与人数一致；来源为 AI 时参与人数为 0。"""
    _submit(client, seed, "stu1", "HAPPY")
    _submit(client, seed, "stu2", "SAD")
    headers = auth_headers(client, "admin")

    one = client.get(
        f"/api/v1/statistics?session_id={seed['ongoing_id']}&user_id={seed['student_ids'][0]}",
        headers=headers,
    )
    assert one.status_code == 200
    data = one.json()["data"]
    assert data["total"] == 1
    assert data["participants"] == 1

    ai = client.get(
        f"/api/v1/statistics?session_id={seed['ongoing_id']}&source=AI", headers=headers
    )
    assert ai.status_code == 200
    assert ai.json()["data"]["total"] == 0
    assert ai.json()["data"]["participants"] == 0


def test_teacher_can_access_classes_and_statistics(client, seed):
    """FR08 教师可使用多维统计与班级候选，但导出仍仅管理员。"""
    headers = auth_headers(client, "teacher_a")
    assert client.get("/api/v1/admin/classes", headers=headers).status_code == 200
    stats = client.get("/api/v1/statistics", headers=headers)
    assert stats.status_code == 200
    assert client.get("/api/v1/admin/emoji/export", headers=headers).status_code == 403
