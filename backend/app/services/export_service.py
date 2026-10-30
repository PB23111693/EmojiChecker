"""CSV 导出服务。列表、统计与导出共用同一套筛选条件，并处理公式注入。"""

from __future__ import annotations

import csv
import datetime as dt
import io

from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.models import Role, User
from app.repositories.audit_repo import AuditRepository
from app.repositories.emoji_repo import EmojiFilters, EmojiRepository
from app.services.stats_service import _local_tz

# 以这些字符开头的单元格会被电子表格软件当作公式执行。
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
MAX_EXPORT_ROWS = 50000

HEADERS = [
    "记录ID",
    "课程",
    "班级",
    "课堂开始时间",
    "学生账号",
    "表情",
    "来源",
    "置信度",
    "观测时间",
    "接收时间",
    "设备",
]


def sanitize_cell(value: object) -> str:
    text = "" if value is None else str(value)
    stripped = text.lstrip()
    if text[:1] in _FORMULA_PREFIXES or stripped[:1] in _FORMULA_PREFIXES:
        return "'" + text
    return text


class ExportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.emoji = EmojiRepository(db)
        self.audit = AuditRepository(db)

    def export(self, user: User, filters: EmojiFilters) -> tuple[bytes, str, int]:
        if user.role == Role.STUDENT:
            raise NotFound("接口不可用")
        scoped = EmojiFilters(
            course_id=filters.course_id,
            session_id=filters.session_id,
            class_name=filters.class_name,
            from_at=filters.from_at,
            to_at=filters.to_at,
            source=filters.source,
            user_id=filters.user_id,
            teacher_id=user.id if user.role == Role.TEACHER else None,
            emotion=filters.emotion,
        )
        rows = self.emoji.iter_all(scoped, limit=MAX_EXPORT_ROWS)
        tz = _local_tz()

        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\r\n")
        writer.writerow(HEADERS)
        for row in rows:
            writer.writerow(
                [
                    row.id,
                    sanitize_cell(row.session.course.name),
                    sanitize_cell(row.session.class_name),
                    row.session.start_at.astimezone(tz).strftime("%Y-%m-%d %H:%M"),
                    sanitize_cell(row.user.username if row.user else ""),
                    row.emotion.value,
                    row.source.value,
                    "" if row.confidence is None else f"{row.confidence:.4f}",
                    row.observed_at.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S"),
                    row.received_at.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S"),
                    sanitize_cell(row.device_id or ""),
                ]
            )

        payload = buffer.getvalue().encode("utf-8-sig")
        stamp = dt.datetime.now(tz).strftime("%Y%m%d_%H%M%S")
        filename = f"emoji_records_{stamp}.csv"
        self.audit.add(
            actor_id=user.id,
            action="ADMIN_EXPORT_EMOJI",
            target_type="emoji_record",
            detail=f"rows={len(rows)} filters={scoped}",
        )
        self.db.commit()
        return payload, filename, len(rows)
