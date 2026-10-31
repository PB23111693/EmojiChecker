"""初始化演示数据。

用法：
    python scripts/seed_demo.py           # 表不存在则建表，已有管理员则跳过
    python scripts/seed_demo.py --reset   # 删除全部表后重建
"""

from __future__ import annotations

import argparse
import datetime as dt
import random
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.security import hash_password  # noqa: E402
from app.db.base import create_all, drop_all, get_session_factory, utcnow  # noqa: E402
from app.models import (  # noqa: E402
    ClassSession,
    Course,
    Emotion,
    EmojiRecord,
    Role,
    ScheduleUser,
    Source,
    User,
    UserStatus,
)

DEMO_PASSWORD = "Emoji@2026"
ADMIN_PASSWORD = "Admin@2026"
DEVICE_ID = "demo-device-01"
MODEL_VERSION = "fer-onnx-1.0"
DISPLAY_TIMEZONE = dt.timezone(dt.timedelta(hours=8))


def _user(username: str, role: Role, password: str) -> User:
    return User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        status=UserStatus.ACTIVE,
    )


def refresh_demo_times() -> None:
    """把已有演示课堂的时间平移到当前时刻，不删除用户与记录。

    初始化与录制相隔多日时，演示课堂会全部过期。本函数只调整
    “软件工程实践”与“数据结构”两门演示课程下课堂的起止时间，
    使其重新处于未开始、进行中、已结束三种状态。
    """
    create_all()
    db = get_session_factory()()
    try:
        now = utcnow()
        courses = {
            course.name: course
            for course in db.query(Course).filter(
                Course.name.in_(["软件工程实践", "数据结构"])
            )
        }
        se_course = courses.get("软件工程实践")
        ds_course = courses.get("数据结构")
        if se_course is None and ds_course is None:
            print("未找到演示课程，请先执行 seed_demo.py 初始化。")
            return

        def _set(session: ClassSession, start: dt.datetime, end: dt.datetime) -> None:
            session.start_at = start.replace(microsecond=0)
            session.end_at = end.replace(microsecond=0)
            session.cancelled = False

        if se_course is not None:
            sessions = (
                db.query(ClassSession)
                .filter(ClassSession.course_id == se_course.id)
                .order_by(ClassSession.id)
                .all()
            )
            by_class: dict[str, list[ClassSession]] = {}
            for item in sessions:
                by_class.setdefault(item.class_name, []).append(item)
            for index, item in enumerate(by_class.get("计科2101", [])):
                if index == 0:
                    _set(item, now - dt.timedelta(minutes=15), now + dt.timedelta(minutes=45))
                elif index == 1:
                    _set(item, now - dt.timedelta(days=1, hours=2), now - dt.timedelta(days=1))
            for item in by_class.get("计科2102", []):
                _set(item, now + dt.timedelta(days=1), now + dt.timedelta(days=1, hours=2))

        if ds_course is not None:
            for index, item in enumerate(
                db.query(ClassSession)
                .filter(ClassSession.course_id == ds_course.id)
                .order_by(ClassSession.id)
                .all()
            ):
                if index == 0:
                    _set(item, now - dt.timedelta(days=2), now - dt.timedelta(days=2) + dt.timedelta(hours=2))

        db.commit()
        print("演示课堂时间已按当前时刻刷新（北京时间 UTC+08:00）。")
        for item in (
            db.query(ClassSession).order_by(ClassSession.id).all()
        ):
            print(
                f"  id={item.id} {item.class_name} "
                f"{item.start_at.astimezone(DISPLAY_TIMEZONE):%Y-%m-%d %H:%M} 至 "
                f"{item.end_at.astimezone(DISPLAY_TIMEZONE):%Y-%m-%d %H:%M}"
            )
    finally:
        db.close()


def seed(reset: bool = False) -> None:
    if reset:
        drop_all()
    create_all()

    db = get_session_factory()()
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if existing is not None:
            print("检测到已存在 admin 账号，本次跳过。需要重建请使用 --reset。")
            return

        now = utcnow()
        admin = _user("admin", Role.ADMIN, ADMIN_PASSWORD)
        teacher_zhang = _user("teacher_zhang", Role.TEACHER, DEMO_PASSWORD)
        teacher_li = _user("teacher_li", Role.TEACHER, DEMO_PASSWORD)
        students = [
            _user(f"stu2021{i:03d}", Role.STUDENT, DEMO_PASSWORD) for i in range(1, 9)
        ]
        db.add_all([admin, teacher_zhang, teacher_li, *students])
        db.commit()

        se_course = Course(name="软件工程实践", teacher_id=teacher_zhang.id)
        ds_course = Course(name="数据结构", teacher_id=teacher_li.id)
        db.add_all([se_course, ds_course])
        db.commit()

        ongoing = ClassSession(
            course_id=se_course.id,
            class_name="计科2101",
            room="实验楼A301",
            start_at=(now - dt.timedelta(minutes=15)).replace(microsecond=0),
            end_at=(now + dt.timedelta(minutes=45)).replace(microsecond=0),
            ai_threshold=0.6,
        )
        ended = ClassSession(
            course_id=se_course.id,
            class_name="计科2101",
            room="实验楼A301",
            start_at=(now - dt.timedelta(days=1, hours=2)).replace(microsecond=0),
            end_at=(now - dt.timedelta(days=1)).replace(microsecond=0),
            ai_threshold=0.6,
        )
        pending = ClassSession(
            course_id=se_course.id,
            class_name="计科2102",
            room="教学楼B204",
            start_at=(now + dt.timedelta(days=1)).replace(microsecond=0),
            end_at=(now + dt.timedelta(days=1, hours=2)).replace(microsecond=0),
            ai_threshold=0.6,
        )
        ds_session = ClassSession(
            course_id=ds_course.id,
            class_name="软工2101",
            room="教学楼C102",
            start_at=(now - dt.timedelta(days=2)).replace(microsecond=0),
            end_at=(now - dt.timedelta(days=2) + dt.timedelta(hours=2)).replace(microsecond=0),
            ai_threshold=0.6,
        )
        db.add_all([ongoing, ended, pending, ds_session])
        db.commit()

        for session in (ongoing, ended, pending, ds_session):
            for student in students:
                db.add(ScheduleUser(session_id=session.id, user_id=student.id))
        db.commit()

        random.seed(20261114)
        emotions = list(Emotion)
        weights = [0.3, 0.28, 0.12, 0.06, 0.12, 0.07, 0.05]

        def _window_seconds(session: ClassSession) -> int:
            """进行中的课堂只生成到当前时刻，避免演示数据出现未来时间。"""
            limit = min(session.end_at, now)
            return max(int((limit - session.start_at).total_seconds()), 1)

        def manual_records(session: ClassSession, count: int) -> None:
            window = _window_seconds(session)
            for index in range(count):
                student = students[index % len(students)]
                observed = session.start_at + dt.timedelta(
                    seconds=random.randint(0, max(window - 1, 0))
                )
                db.add(
                    EmojiRecord(
                        event_id=f"seed-m-{session.id}-{index}",
                        session_id=session.id,
                        user_id=student.id,
                        emotion=random.choices(emotions, weights=weights, k=1)[0],
                        source=Source.MANUAL,
                        observed_at=observed,
                        received_at=observed + dt.timedelta(seconds=1),
                        manual_slot=None,
                    )
                )

        def ai_records(session: ClassSession, count: int) -> None:
            window = _window_seconds(session)
            for index in range(count):
                observed = session.start_at + dt.timedelta(
                    seconds=random.randint(0, max(window - 1, 0))
                )
                db.add(
                    EmojiRecord(
                        event_id=f"seed-a-{session.id}-{index}",
                        session_id=session.id,
                        user_id=None,
                        emotion=random.choices(emotions, weights=weights, k=1)[0],
                        source=Source.AI,
                        confidence=round(random.uniform(0.62, 0.97), 4),
                        device_id=DEVICE_ID,
                        model_version=MODEL_VERSION,
                        observed_at=observed,
                        received_at=observed + dt.timedelta(seconds=2),
                        manual_slot=None,
                    )
                )

        manual_records(ended, 112)
        ai_records(ended, 68)
        manual_records(ongoing, 14)
        ai_records(ongoing, 22)
        manual_records(ds_session, 40)
        ai_records(ds_session, 18)
        db.commit()

        print("演示数据初始化完成。")
        print(f"  管理员    admin / {ADMIN_PASSWORD}")
        print(f"  教师      teacher_zhang / {DEMO_PASSWORD}")
        print(f"  教师      teacher_li / {DEMO_PASSWORD}")
        print(f"  学生      stu2021001 至 stu2021008 / {DEMO_PASSWORD}")
        print(f"  进行中课堂 id={ongoing.id}，已结束课堂 id={ended.id}，未开始课堂 id={pending.id}")
        print(f"  历史手动记录 {112 + 14 + 40} 条，AI 记录 {68 + 22 + 18} 条")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="初始化演示数据")
    parser.add_argument("--reset", action="store_true", help="删除全部表后重建")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="只把演示课堂时间平移到当前时刻，保留用户与历史记录",
    )
    args = parser.parse_args()
    if args.refresh:
        refresh_demo_times()
    else:
        seed(reset=args.reset)
