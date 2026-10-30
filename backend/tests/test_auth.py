"""认证用例。对应验收矩阵 AT01 与 AT15 的注册越权分支。"""

from __future__ import annotations

from tests.conftest import DEFAULT_PASSWORD, auth_headers


def test_register_login_and_change_password(client):
    """AT01 学生注册成功，密码正确才能登录，改密后旧令牌立即失效。"""
    payload = {"username": "newstudent", "password": "Abc12345"}
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["data"]["role"] == "STUDENT"
    assert body["request_id"]

    wrong = client.post(
        "/api/v1/auth/login", json={"username": "newstudent", "password": "wrong-pass1"}
    )
    assert wrong.status_code == 401
    assert wrong.json()["code"] == 40101

    login = client.post("/api/v1/auth/login", json=payload)
    assert login.status_code == 200
    old_token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {old_token}"}

    assert client.get("/api/v1/users/me", headers=headers).status_code == 200

    change = client.put(
        "/api/v1/auth/password",
        json={"old_password": "Abc12345", "new_password": "Xyz98765"},
        headers=headers,
    )
    assert change.status_code == 200

    expired = client.get("/api/v1/users/me", headers=headers)
    assert expired.status_code == 401

    relogin = client.post(
        "/api/v1/auth/login", json={"username": "newstudent", "password": "Xyz98765"}
    )
    assert relogin.status_code == 200


def test_register_rejects_admin_role_without_invite(client):
    """AT15 未携带管理员邀请码时注册 ADMIN 返回 422，且不产生账号。"""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "sneaky", "password": "Abc12345", "role": "ADMIN"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == 42200

    login = client.post(
        "/api/v1/auth/login", json={"username": "sneaky", "password": "Abc12345"}
    )
    assert login.status_code == 401


def test_admin_register_requires_invite_code(client):
    """AT01 管理员凭独立邀请码注册，错误邀请码被拒绝且不产生账号。"""
    wrong = client.post(
        "/api/v1/auth/register",
        json={
            "username": "admin_new",
            "password": "Abc12345",
            "role": "ADMIN",
            "invite_code": "bad-code",
        },
    )
    assert wrong.status_code == 422

    ok = client.post(
        "/api/v1/auth/register",
        json={
            "username": "admin_new",
            "password": "Abc12345",
            "role": "ADMIN",
            "invite_code": "ADMIN-INVITE",
        },
    )
    assert ok.status_code == 201
    assert ok.json()["data"]["role"] == "ADMIN"

    headers = auth_headers(client, "admin_new", "Abc12345")
    assert client.get("/api/v1/admin/users", headers=headers).status_code == 200


def test_register_duplicate_username(client):
    body = {"username": "dupuser", "password": "Abc12345"}
    assert client.post("/api/v1/auth/register", json=body).status_code == 201
    again = client.post("/api/v1/auth/register", json=body)
    assert again.status_code == 409


def test_register_weak_password(client):
    response = client.post(
        "/api/v1/auth/register", json={"username": "weakuser", "password": "abcdefgh"}
    )
    assert response.status_code == 422
    assert "数字" in response.json()["message"]


def test_teacher_register_requires_invite_code(client):
    without_code = client.post(
        "/api/v1/auth/register",
        json={"username": "teacher_x", "password": "Abc12345", "role": "TEACHER"},
    )
    assert without_code.status_code == 422

    wrong_code = client.post(
        "/api/v1/auth/register",
        json={
            "username": "teacher_x",
            "password": "Abc12345",
            "role": "TEACHER",
            "invite_code": "bad-code",
        },
    )
    assert wrong_code.status_code == 422

    ok = client.post(
        "/api/v1/auth/register",
        json={
            "username": "teacher_x",
            "password": "Abc12345",
            "role": "TEACHER",
            "invite_code": "TEACH-INVITE",
        },
    )
    assert ok.status_code == 201
    assert ok.json()["data"]["role"] == "TEACHER"


def test_disabled_user_cannot_login_or_use_token(client, seed):
    headers = auth_headers(client, "stu1")
    admin_headers = auth_headers(client, "admin")
    student_id = seed["student_ids"][0]

    response = client.patch(
        f"/api/v1/admin/users/{student_id}/status",
        json={"status": "DISABLED"},
        headers=admin_headers,
    )
    assert response.status_code == 200

    assert client.get("/api/v1/users/me", headers=headers).status_code == 401
    login = client.post(
        "/api/v1/auth/login", json={"username": "stu1", "password": DEFAULT_PASSWORD}
    )
    assert login.status_code == 403


def test_admin_cannot_disable_self(client, seed):
    admin_headers = auth_headers(client, "admin")
    response = client.patch(
        f"/api/v1/admin/users/{seed['admin_id']}/status",
        json={"status": "DISABLED"},
        headers=admin_headers,
    )
    assert response.status_code == 409
