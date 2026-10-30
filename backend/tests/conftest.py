"""测试基座。使用内存 SQLite 与 StaticPool，保证接口线程与主线程共享同一份数据。"""

from __future__ import annotations

import datetime as dt
import os

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "unit-test-secret-key-not-for-production"
os.environ["MANUAL_SLOT_SECONDS"] = "0"
os.environ["TEACHER_INVITE_CODE"] = "TEACH-INVITE"
os.environ["ADMIN_INVITE_CODE"] = "ADMIN-INVITE"
os.environ["AI_SERVICE_KEY"] = "test-ai-key"
os.environ["AI_DEVICE_ID"] = "test-device"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.ratelimit import emoji_limiter, login_limiter  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db import base as db_base  # noqa: E402
from app.db.base import utcnow  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Base,
    ClassSession,
    Course,
    Role,
    ScheduleUser,
    User,
    UserStatus,
)

DEFAULT_PASSWORD = "Passw0rd1"


@pytest.fixture()
def client() -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db_base._engine = engine
    db_base._session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    login_limiter.reset()
    emoji_limiter.reset()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db():
    session = db_base.get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def seed(client: TestClient, db):
    now = utcnow()

    admin = User(
        username="admin",
        password_hash=hash_password(DEFAULT_PASSWORD),
        role=Role.ADMIN,
        status=UserStatus.ACTIVE,
    )
    teacher = User(
        username="teacher_a",
        password_hash=hash_password(DEFAULT_PASSWORD),
        role=Role.TEACHER,
        status=UserStatus.ACTIVE,
    )
    other_teacher = User(
        username="teacher_b",
        password_hash=hash_password(DEFAULT_PASSWORD),
        role=Role.TEACHER,
        status=UserStatus.ACTIVE,
    )
    students = [
        User(
            username=f"stu{i}",
            password_hash=hash_password(DEFAULT_PASSWORD),
            role=Role.STUDENT,
            status=UserStatus.ACTIVE,
        )
        for i in range(1, 4)
    ]
    db.add_all([admin, teacher, other_teacher, *students])
    db.commit()

    course = Course(name="软件工程实践", teacher_id=teacher.id)
    other_course = Course(name="数据结构", teacher_id=other_teacher.id)
    db.add_all([course, other_course])
    db.commit()

    ongoing = ClassSession(
        course_id=course.id,
        class_name="计科2101",
        room="A101",
        start_at=now - dt.timedelta(minutes=10),
        end_at=now + dt.timedelta(minutes=50),
        ai_threshold=0.6,
    )
    pending = ClassSession(
        course_id=course.id,
        class_name="计科2102",
        room="A102",
        start_at=now + dt.timedelta(hours=2),
        end_at=now + dt.timedelta(hours=4),
        ai_threshold=0.6,
    )
    ended = ClassSession(
        course_id=course.id,
        class_name="计科2101",
        room="A101",
        start_at=now - dt.timedelta(hours=3),
        end_at=now - dt.timedelta(hours=2),
        ai_threshold=0.6,
    )
    foreign = ClassSession(
        course_id=other_course.id,
        class_name="软工2101",
        room="B201",
        start_at=now - dt.timedelta(minutes=5),
        end_at=now + dt.timedelta(minutes=55),
        ai_threshold=0.6,
    )
    db.add_all([ongoing, pending, ended, foreign])
    db.commit()

    for student in students:
        db.add(ScheduleUser(session_id=ongoing.id, user_id=student.id))
    db.commit()

    return {
        "admin_id": admin.id,
        "teacher_id": teacher.id,
        "other_teacher_id": other_teacher.id,
        "student_ids": [item.id for item in students],
        "course_id": course.id,
        "other_course_id": other_course.id,
        "ongoing_id": ongoing.id,
        "pending_id": pending.id,
        "ended_id": ended.id,
        "foreign_id": foreign.id,
    }


def auth_headers(client: TestClient, username: str, password: str = DEFAULT_PASSWORD) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
