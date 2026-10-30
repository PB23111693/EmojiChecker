"""运行时配置。所有配置项来自环境变量或项目根目录的 .env 文件。"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


def _load_dotenv(path: Path) -> None:
    """最小实现的环境文件加载器，不覆盖已存在的进程环境变量。"""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(PROJECT_ROOT / ".env")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_str(name: str, default: str = "") -> str:
    return os.environ.get(name, "").strip() or default


def _resolve_sqlite_url(url: str) -> str:
    """把相对路径的 SQLite 连接串固定到项目根目录，避免依赖工作目录。"""
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return url
    raw_path = url[len(prefix) :]
    if raw_path.startswith(":memory:") or raw_path.startswith("/"):
        return url
    absolute = (PROJECT_ROOT / raw_path).resolve()
    absolute.parent.mkdir(parents=True, exist_ok=True)
    return f"{prefix}{absolute.as_posix()}"


@dataclass(frozen=True)
class Settings:
    app_name: str
    env: str
    log_level: str
    secret_key: str
    access_token_minutes: int
    database_url: str
    auto_create_tables: bool
    cors_origins: tuple[str, ...]
    manual_slot_seconds: int
    default_page_size: int
    max_page_size: int
    teacher_invite_code: str
    admin_invite_code: str
    ai_service_key: str
    ai_device_id: str
    ai_allowed_session_ids: tuple[int, ...]
    ai_max_past_seconds: int
    ai_max_future_seconds: int
    timezone: str = "Asia/Shanghai"
    is_test: bool = False
    secret_key_is_ephemeral: bool = field(default=False)

    @property
    def is_dev(self) -> bool:
        return self.env == "dev"


def load_settings() -> Settings:
    raw_secret = _env_str("SECRET_KEY")
    env = _env_str("APP_ENV", "dev")
    ephemeral = not raw_secret
    if ephemeral:
        # 未配置密钥时生成进程级密钥，重启后旧令牌全部失效。
        # 这是有意为之的失败安全策略：不把默认密钥写进仓库。
        raw_secret = secrets.token_urlsafe(48)

    database_url = _env_str("DATABASE_URL", "sqlite:///./data/se_emoji.db")
    origins = tuple(
        item.strip()
        for item in _env_str("CORS_ORIGINS", "http://localhost:5173").split(",")
        if item.strip()
    )
    session_ids = tuple(
        int(item)
        for item in _env_str("AI_ALLOWED_SESSION_IDS").split(",")
        if item.strip().isdigit()
    )

    return Settings(
        app_name=_env_str("APP_NAME", "表情符号课堂情绪检查器"),
        env=env,
        log_level=_env_str("LOG_LEVEL", "INFO").upper(),
        secret_key=raw_secret,
        access_token_minutes=_env_int("ACCESS_TOKEN_MINUTES", 60),
        database_url=_resolve_sqlite_url(database_url),
        auto_create_tables=_env_bool("AUTO_CREATE_TABLES", True),
        cors_origins=origins,
        manual_slot_seconds=_env_int("MANUAL_SLOT_SECONDS", 30),
        default_page_size=_env_int("DEFAULT_PAGE_SIZE", 20),
        max_page_size=_env_int("MAX_PAGE_SIZE", 100),
        teacher_invite_code=_env_str("TEACHER_INVITE_CODE"),
        admin_invite_code=_env_str("ADMIN_INVITE_CODE"),
        ai_service_key=_env_str("AI_SERVICE_KEY"),
        ai_device_id=_env_str("AI_DEVICE_ID", "demo-device-01"),
        ai_allowed_session_ids=session_ids,
        ai_max_past_seconds=_env_int("AI_MAX_PAST_SECONDS", 60),
        ai_max_future_seconds=_env_int("AI_MAX_FUTURE_SECONDS", 5),
        is_test=env == "test",
        secret_key_is_ephemeral=ephemeral,
    )


settings = load_settings()
