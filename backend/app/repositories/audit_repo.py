"""审计日志数据访问。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(
        self,
        *,
        actor_id: int | None,
        action: str,
        target_type: str | None = None,
        target_id: str | None = None,
        result: str = "SUCCESS",
        detail: str | None = None,
    ) -> AuditLog:
        log = AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            result=result,
            detail=detail,
        )
        self.db.add(log)
        self.db.flush()
        return log

    def list(self, *, page: int, page_size: int, action: str | None = None) -> tuple[list[AuditLog], int]:
        conditions = []
        if action:
            conditions.append(AuditLog.action == action)
        total = int(
            self.db.scalar(select(func.count()).select_from(AuditLog).where(*conditions)) or 0
        )
        stmt = (
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.db.scalars(stmt)), total
