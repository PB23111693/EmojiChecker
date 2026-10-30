"""实时看板 WebSocket。只推送变更信号，业务数据仍由 REST 拉取。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.errors import AppError
from app.core.realtime import hub
from app.core.security import decode_access_token
from app.db.base import get_session_factory
from app.models import Role, User, UserStatus
from app.repositories.catalog_repo import SessionRepository

router = APIRouter(tags=["实时看板"])
logger = logging.getLogger(__name__)


def _authenticate(token: str, session_id: int) -> User:
    payload = decode_access_token(token)
    db = get_session_factory()()
    try:
        user = db.get(User, int(payload.get("sub", "0")))
        if user is None or user.status != UserStatus.ACTIVE:
            raise AppError("账号不可用", code=40100, status_code=401)
        if int(payload.get("av", -1)) != user.auth_version:
            raise AppError("登录已失效", code=40100, status_code=401)
        session = SessionRepository(db).get(session_id)
        if session is None:
            raise AppError("课堂不存在", code=40400, status_code=404)
        if user.role == Role.TEACHER and session.course.teacher_id != user.id:
            raise AppError("课堂不存在", code=40400, status_code=404)
        if user.role == Role.STUDENT and not SessionRepository(db).is_member(
            session_id, user.id
        ):
            raise AppError("课堂不存在", code=40400, status_code=404)
        db.expunge(user)
        return user
    finally:
        db.close()


@router.websocket("/ws/dashboard")
async def dashboard_socket(websocket: WebSocket, session_id: int, token: str) -> None:
    try:
        _authenticate(token, session_id)
    except AppError as exc:
        await websocket.close(code=4401, reason=exc.message)
        return
    except Exception:
        await websocket.close(code=4401, reason="认证失败")
        return

    await websocket.accept()
    await hub.subscribe(session_id, websocket)
    await websocket.send_json({"type": "connected", "session_id": session_id})
    try:
        while True:
            # 客户端保活消息，不使用其内容。
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await hub.unsubscribe(session_id, websocket)
