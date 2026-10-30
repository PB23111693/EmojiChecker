"""课程、课堂与名单服务。课堂状态与冻结规则见设计方案 3.1。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.models import (
    ClassSession,
    Course,
    Role,
    SessionStatus,
    User,
    UserStatus,
    compute_session_status,
)
from app.repositories.audit_repo import AuditRepository
from app.repositories.catalog_repo import CourseRepository, SessionRepository
from app.repositories.emoji_repo import EmojiRepository
from app.repositories.user_repo import UserRepository
from app.schemas.catalog import (
    CourseCreateRequest,
    CourseOut,
    MemberOut,
    MembersOut,
    SessionCreateRequest,
    SessionOut,
    SessionUpdateRequest,
)
from app.schemas.stats import ClassOption
from app.db.base import utcnow


class CatalogService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.courses = CourseRepository(db)
        self.sessions = SessionRepository(db)
        self.users = UserRepository(db)
        self.emoji = EmojiRepository(db)
        self.audit = AuditRepository(db)

    # ---------- 课程 ----------

    def list_courses(self, user: User) -> list[CourseOut]:
        if user.role == Role.TEACHER:
            courses = self.courses.list(teacher_id=user.id)
        elif user.role == Role.ADMIN:
            courses = self.courses.list()
        else:
            scoped_sessions, _ = self.sessions.list(
                teacher_id=None,
                course_id=None,
                class_name=None,
                status=None,
                student_id=user.id,
                now=utcnow(),
                page=1,
                page_size=1000,
            )
            course_ids = sorted({item.course_id for item in scoped_sessions})
            courses = self.courses.list_by_ids(course_ids)

        counts = self.courses.session_counts([item.id for item in courses])
        return [
            CourseOut(
                id=item.id,
                name=item.name,
                teacher_id=item.teacher_id,
                teacher_name=item.teacher.username if item.teacher else None,
                session_count=counts.get(item.id, 0),
                created_at=item.created_at,
            )
            for item in courses
        ]

    def create_course(self, payload: CourseCreateRequest, actor: User) -> CourseOut:
        teacher = self.users.get(payload.teacher_id)
        if teacher is None or teacher.role != Role.TEACHER:
            raise ValidationFailed("指定的教师不存在或角色不是教师")
        if teacher.status != UserStatus.ACTIVE:
            raise ValidationFailed("指定的教师账号已停用")
        if self.courses.exists(name=payload.name, teacher_id=teacher.id):
            raise Conflict("该教师已存在同名课程")

        course = self.courses.create(name=payload.name, teacher_id=teacher.id)
        self.audit.add(
            actor_id=actor.id,
            action="ADMIN_CREATE_COURSE",
            target_type="course",
            target_id=str(course.id),
            detail=f"name={course.name}",
        )
        self.db.commit()
        return CourseOut(
            id=course.id,
            name=course.name,
            teacher_id=course.teacher_id,
            teacher_name=teacher.username,
            session_count=0,
            created_at=course.created_at,
        )

    # ---------- 课堂 ----------

    def _status(self, session: ClassSession, now: dt.datetime | None = None) -> SessionStatus:
        return compute_session_status(session.start_at, session.end_at, session.cancelled, now)

    def _visible_session(self, session_id: int, user: User) -> ClassSession:
        session = self.sessions.get(session_id)
        if session is None:
            raise NotFound("课堂不存在")
        if user.role == Role.ADMIN:
            return session
        if user.role == Role.TEACHER:
            if session.course.teacher_id != user.id:
                raise NotFound("课堂不存在")
            return session
        if not self.sessions.is_member(session.id, user.id):
            raise NotFound("课堂不存在")
        return session

    def get_session(self, session_id: int, user: User) -> SessionOut:
        session = self._visible_session(session_id, user)
        return self._to_out(session)

    def _to_out(self, session: ClassSession, now: dt.datetime | None = None) -> SessionOut:
        counts = self.emoji.source_counts_by_session([session.id]).get(session.id, {})
        return SessionOut(
            id=session.id,
            course_id=session.course_id,
            course_name=session.course.name,
            teacher_id=session.course.teacher_id,
            teacher_name=session.course.teacher.username,
            class_name=session.class_name,
            room=session.room,
            start_at=session.start_at,
            end_at=session.end_at,
            cancelled=session.cancelled,
            ai_threshold=session.ai_threshold,
            status=self._status(session, now),
            member_count=self.sessions.member_count(session.id),
            manual_count=counts.get("MANUAL", 0),
            ai_count=counts.get("AI", 0),
        )

    def list_sessions(
        self,
        user: User,
        *,
        course_id: int | None,
        class_name: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[SessionOut], int]:
        now = utcnow()
        teacher_id = user.id if user.role == Role.TEACHER else None
        student_id = user.id if user.role == Role.STUDENT else None
        rows, total = self.sessions.list(
            teacher_id=teacher_id,
            course_id=course_id,
            class_name=class_name,
            status=status,
            student_id=student_id,
            now=now,
            page=page,
            page_size=page_size,
        )
        ids = [item.id for item in rows]
        counts = self.emoji.source_counts_by_session(ids)
        member_counts = self.sessions.member_counts(ids)
        result = []
        for item in rows:
            scoped = counts.get(item.id, {})
            result.append(
                SessionOut(
                    id=item.id,
                    course_id=item.course_id,
                    course_name=item.course.name,
                    teacher_id=item.course.teacher_id,
                    teacher_name=item.course.teacher.username,
                    class_name=item.class_name,
                    room=item.room,
                    start_at=item.start_at,
                    end_at=item.end_at,
                    cancelled=item.cancelled,
                    ai_threshold=item.ai_threshold,
                    status=self._status(item, now),
                    member_count=member_counts.get(item.id, 0),
                    manual_count=scoped.get("MANUAL", 0),
                    ai_count=scoped.get("AI", 0),
                )
            )
        return result, total

    def create_session(self, payload: SessionCreateRequest, actor: User) -> SessionOut:
        course = self.courses.get(payload.course_id)
        if course is None:
            raise ValidationFailed("课程不存在")
        session = self.sessions.create(
            course_id=course.id,
            class_name=payload.class_name,
            room=payload.room,
            start_at=payload.start_at,
            end_at=payload.end_at,
            ai_threshold=payload.ai_threshold,
        )
        self.audit.add(
            actor_id=actor.id,
            action="ADMIN_CREATE_SESSION",
            target_type="session",
            target_id=str(session.id),
            detail=f"course={course.id} class={session.class_name}",
        )
        self.db.commit()
        return self._to_out(session)

    def update_session(
        self, session_id: int, payload: SessionUpdateRequest, actor: User
    ) -> SessionOut:
        session = self.sessions.get(session_id)
        if session is None:
            raise NotFound("课堂不存在")
        status = self._status(session)
        if status != SessionStatus.PENDING:
            raise Conflict("课堂已开始、已结束或已取消，设置已冻结")

        new_start = payload.start_at or session.start_at
        new_end = payload.end_at or session.end_at
        if new_end <= new_start:
            raise ValidationFailed("结束时间必须晚于开始时间")

        if payload.class_name is not None:
            session.class_name = payload.class_name
        if payload.room is not None:
            session.room = payload.room
        if payload.start_at is not None:
            session.start_at = payload.start_at
        if payload.end_at is not None:
            session.end_at = payload.end_at
        if payload.ai_threshold is not None:
            session.ai_threshold = payload.ai_threshold
        if payload.cancelled is not None:
            session.cancelled = payload.cancelled

        self.audit.add(
            actor_id=actor.id,
            action="ADMIN_UPDATE_SESSION",
            target_type="session",
            target_id=str(session.id),
        )
        self.db.commit()
        self.db.refresh(session)
        return self._to_out(session)

    # ---------- 名单 ----------

    def list_members(self, session_id: int, user: User) -> MembersOut:
        session = self._visible_session(session_id, user)
        rows = self.sessions.list_members(session.id)
        return MembersOut(
            session_id=session.id,
            member_count=len(rows),
            items=[
                MemberOut(
                    user_id=row.user_id,
                    username=row.user.username if row.user else "",
                    arranged_at=row.arranged_at,
                )
                for row in rows
            ],
        )

    def replace_members(self, session_id: int, user_ids: list[int], actor: User) -> MembersOut:
        session = self.sessions.get(session_id)
        if session is None:
            raise NotFound("课堂不存在")
        if self._status(session) != SessionStatus.PENDING:
            raise Conflict("课堂已开始或已结束，名单不可修改")

        unique_ids = sorted({uid for uid in user_ids if uid > 0})
        users = self.users.list_by_ids(unique_ids)
        found = {item.id: item for item in users}
        missing = [uid for uid in unique_ids if uid not in found]
        if missing:
            raise ValidationFailed(f"以下用户不存在：{missing}")
        wrong_role = [item.username for item in users if item.role != Role.STUDENT]
        if wrong_role:
            raise ValidationFailed(f"以下用户不是学生：{', '.join(wrong_role)}")
        inactive = [item.username for item in users if item.status != UserStatus.ACTIVE]
        if inactive:
            raise ValidationFailed(f"以下学生账号已停用：{', '.join(inactive)}")

        count = self.sessions.replace_members(session.id, unique_ids)
        self.audit.add(
            actor_id=actor.id,
            action="ADMIN_UPDATE_SCHEDULE",
            target_type="session",
            target_id=str(session.id),
            detail=f"members={count}",
        )
        self.db.commit()
        return self.list_members(session.id, actor)

    def class_options(self, user: User) -> list[ClassOption]:
        teacher_id = user.id if user.role == Role.TEACHER else None
        return [
            ClassOption(class_name=name, session_count=count)
            for name, count in self.sessions.class_names(teacher_id=teacher_id)
        ]

    def assert_teacher_owns(self, session: ClassSession, user: User) -> None:
        if user.role == Role.TEACHER and session.course.teacher_id != user.id:
            raise Forbidden("只能查看本人所授课程")
