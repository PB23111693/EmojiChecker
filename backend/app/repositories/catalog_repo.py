"""课程、课堂与名单数据访问。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload

from app.models import ClassSession, Course, Role, ScheduleUser, User


class CourseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, course_id: int) -> Course | None:
        return self.db.get(Course, course_id)

    def list(self, *, teacher_id: int | None = None) -> list[Course]:
        stmt = select(Course).options(joinedload(Course.teacher)).order_by(Course.id.desc())
        if teacher_id is not None:
            stmt = stmt.where(Course.teacher_id == teacher_id)
        return list(self.db.scalars(stmt))

    def list_by_ids(self, course_ids: list[int]) -> list[Course]:
        if not course_ids:
            return []
        stmt = (
            select(Course)
            .options(joinedload(Course.teacher))
            .where(Course.id.in_(course_ids))
            .order_by(Course.id.desc())
        )
        return list(self.db.scalars(stmt))

    def create(self, *, name: str, teacher_id: int) -> Course:
        course = Course(name=name, teacher_id=teacher_id)
        self.db.add(course)
        self.db.flush()
        return course

    def exists(self, *, name: str, teacher_id: int) -> bool:
        stmt = select(func.count()).select_from(Course).where(
            Course.name == name, Course.teacher_id == teacher_id
        )
        return bool(self.db.scalar(stmt))

    def session_counts(self, course_ids: list[int]) -> dict[int, int]:
        if not course_ids:
            return {}
        stmt = (
            select(ClassSession.course_id, func.count())
            .where(ClassSession.course_id.in_(course_ids))
            .group_by(ClassSession.course_id)
        )
        return {int(cid): int(count) for cid, count in self.db.execute(stmt).all()}

    def teachers(self) -> list[User]:
        return list(
            self.db.scalars(
                select(User).where(User.role == Role.TEACHER).order_by(User.username)
            )
        )


class SessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, session_id: int) -> ClassSession | None:
        return self.db.get(ClassSession, session_id)

    def create(
        self,
        *,
        course_id: int,
        class_name: str,
        room: str | None,
        start_at: dt.datetime,
        end_at: dt.datetime,
        ai_threshold: float,
    ) -> ClassSession:
        session = ClassSession(
            course_id=course_id,
            class_name=class_name,
            room=room,
            start_at=start_at,
            end_at=end_at,
            ai_threshold=ai_threshold,
            cancelled=False,
        )
        self.db.add(session)
        self.db.flush()
        return session

    def list(
        self,
        *,
        teacher_id: int | None,
        course_id: int | None,
        class_name: str | None,
        status: str | None,
        student_id: int | None,
        now: dt.datetime,
        page: int,
        page_size: int,
    ) -> tuple[list[ClassSession], int]:
        stmt = select(ClassSession).options(
            joinedload(ClassSession.course).joinedload(Course.teacher)
        )
        conditions = []
        if teacher_id is not None:
            stmt = stmt.join(Course, ClassSession.course_id == Course.id)
            conditions.append(Course.teacher_id == teacher_id)
        if course_id is not None:
            conditions.append(ClassSession.course_id == course_id)
        if class_name is not None:
            conditions.append(ClassSession.class_name == class_name)
        if student_id is not None:
            stmt = stmt.join(ScheduleUser, ScheduleUser.session_id == ClassSession.id)
            conditions.append(ScheduleUser.user_id == student_id)
        if status == "PENDING":
            conditions.append(ClassSession.cancelled.is_(False))
            conditions.append(ClassSession.start_at > now)
        elif status == "ONGOING":
            conditions.append(ClassSession.cancelled.is_(False))
            conditions.append(ClassSession.start_at <= now)
            conditions.append(ClassSession.end_at > now)
        elif status == "ENDED":
            conditions.append(ClassSession.cancelled.is_(False))
            conditions.append(ClassSession.end_at <= now)
        elif status == "CANCELLED":
            conditions.append(ClassSession.cancelled.is_(True))

        stmt = stmt.where(*conditions)
        subquery = stmt.order_by(None).subquery()
        total = int(self.db.scalar(select(func.count()).select_from(subquery)) or 0)
        rows = list(
            self.db.scalars(
                stmt.order_by(ClassSession.start_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return rows, total

    def member_ids(self, session_id: int) -> list[int]:
        return list(
            self.db.scalars(
                select(ScheduleUser.user_id).where(ScheduleUser.session_id == session_id)
            )
        )

    def member_count(self, session_id: int) -> int:
        return int(
            self.db.scalar(
                select(func.count()).select_from(ScheduleUser).where(
                    ScheduleUser.session_id == session_id
                )
            )
            or 0
        )

    def member_counts(self, session_ids: list[int]) -> dict[int, int]:
        if not session_ids:
            return {}
        stmt = (
            select(ScheduleUser.session_id, func.count())
            .where(ScheduleUser.session_id.in_(session_ids))
            .group_by(ScheduleUser.session_id)
        )
        return {int(sid): int(count) for sid, count in self.db.execute(stmt).all()}

    def is_member(self, session_id: int, user_id: int) -> bool:
        stmt = select(func.count()).select_from(ScheduleUser).where(
            ScheduleUser.session_id == session_id, ScheduleUser.user_id == user_id
        )
        return bool(self.db.scalar(stmt))

    def replace_members(self, session_id: int, user_ids: list[int]) -> int:
        self.db.execute(delete(ScheduleUser).where(ScheduleUser.session_id == session_id))
        unique_ids = sorted({uid for uid in user_ids if uid > 0})
        for uid in unique_ids:
            self.db.add(ScheduleUser(session_id=session_id, user_id=uid))
        self.db.flush()
        return len(unique_ids)

    def list_members(self, session_id: int) -> list[ScheduleUser]:
        return list(
            self.db.scalars(
                select(ScheduleUser)
                .options(joinedload(ScheduleUser.user))
                .where(ScheduleUser.session_id == session_id)
                .order_by(ScheduleUser.user_id)
            )
        )

    def class_names(self, *, teacher_id: int | None) -> list[tuple[str, int]]:
        stmt = select(ClassSession.class_name, func.count())
        if teacher_id is not None:
            stmt = stmt.join(Course, ClassSession.course_id == Course.id).where(
                Course.teacher_id == teacher_id
            )
        stmt = stmt.group_by(ClassSession.class_name).order_by(ClassSession.class_name)
        return [(str(name), int(count)) for name, count in self.db.execute(stmt).all()]
