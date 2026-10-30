"""管理员与审计日志用例。对应 AT02 的受控创建与 FR11 的关键操作留痕。"""

from __future__ import annotations

from tests.conftest import auth_headers


def test_admin_creates_user_and_writes_audit_log(client, seed):
    headers = auth_headers(client, "admin")
    created = client.post(
        "/api/v1/admin/users",
        json={
            "username": "stu2099001",
            "password": "Emoji2026x",
            "role": "STUDENT",
            "email": "stu2099001@example.com",
        },
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["data"]["role"] == "STUDENT"

    logs = client.get(
        "/api/v1/admin/audit-logs?action=ADMIN_CREATE_USER", headers=headers
    )
    assert logs.status_code == 200
    body = logs.json()["data"]
    assert body["total"] >= 1
    assert body["items"][0]["action"] == "ADMIN_CREATE_USER"


def test_audit_log_requires_admin(client, seed):
    response = client.get(
        "/api/v1/admin/audit-logs", headers=auth_headers(client, "stu1")
    )
    assert response.status_code == 403


def test_cannot_create_admin_account(client, seed):
    response = client.post(
        "/api/v1/admin/users",
        json={"username": "admin2", "password": "Emoji2026x", "role": "ADMIN"},
        headers=auth_headers(client, "admin"),
    )
    assert response.status_code == 422


def test_duplicate_username_rejected(client, seed):
    response = client.post(
        "/api/v1/admin/users",
        json={"username": "stu1", "password": "Emoji2026x", "role": "STUDENT"},
        headers=auth_headers(client, "admin"),
    )
    assert response.status_code == 409


def test_disable_user_invalidates_token(client, seed):
    """AT01 与 FR11 停用账号后旧令牌立即失效。"""
    target_id = seed["student_ids"][1]
    target_headers = auth_headers(client, "stu2")
    assert client.get("/api/v1/users/me", headers=target_headers).status_code == 200

    disabled = client.patch(
        f"/api/v1/admin/users/{target_id}/status",
        json={"status": "DISABLED"},
        headers=auth_headers(client, "admin"),
    )
    assert disabled.status_code == 200
    assert client.get("/api/v1/users/me", headers=target_headers).status_code == 401
