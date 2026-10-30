"""应用入口。装配中间件、异常处理、路由与前端静态资源。"""

from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.controllers import ai as ai_controller
from app.controllers import analytics, audit, auth, catalog, emoji, users, ws
from app.core.config import PROJECT_ROOT, settings
from app.core.context import fail, set_request_id
from app.core.errors import AppError
from app.core.realtime import hub
from app.db.base import create_all

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if settings.secret_key_is_ephemeral:
        logger.warning("未配置 SECRET_KEY，本次进程使用临时密钥，重启后所有令牌失效")
    if settings.auto_create_tables:
        create_all()
        logger.info("数据表已就绪：%s", settings.database_url)
    hub.bind_loop(asyncio.get_running_loop())
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "软件工程实践课程大作业。学生主动反馈课堂感受，AI 进程上报匿名表情分类结果，"
        "教师查看所授课堂的实时看板，管理员完成排课、统计与导出。"
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-Export-Rows", "X-Request-Id"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
    set_request_id(request_id)
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=fail(exc.code, exc.message, jsonable_encoder(exc.errors)),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {
            "loc": list(error.get("loc", [])),
            "msg": error.get("msg", ""),
            "type": error.get("type", ""),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=fail(42200, "请求参数不合法", details),
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "请求无法处理"
    return JSONResponse(
        status_code=exc.status_code,
        content=fail(exc.status_code * 100, message),
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("未处理异常 path=%s", request.url.path)
    return JSONResponse(status_code=500, content=fail(50000, "服务内部错误"))


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(catalog.router)
app.include_router(emoji.router)
app.include_router(analytics.router)
app.include_router(audit.router)
app.include_router(ai_controller.router)
app.include_router(ws.router)


@app.get("/health", tags=["运维"], summary="健康检查")
def health() -> dict:
    return {
        "status": "ok",
        "env": settings.env,
        "database": settings.database_url.split("://", 1)[0],
    }


_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"
if _DIST_DIR.is_dir():
    app.mount("/", StaticFiles(directory=_DIST_DIR, html=True), name="web")
else:

    @app.get("/", tags=["运维"], summary="未构建前端时的占位页")
    def index() -> dict:
        return {
            "message": "后端已启动，前端尚未构建。",
            "docs": "/docs",
            "openapi": "/openapi.json",
        }


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
