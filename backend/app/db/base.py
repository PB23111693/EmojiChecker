"""数据库引擎、会话工厂与通用类型。"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator
from typing import Any

from sqlalchemy import BigInteger, DateTime, Integer, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.core.config import settings

# SQLite 只有声明为 INTEGER PRIMARY KEY 的列才具备自增 rowid 语义，
# 因此主键类型在 SQLite 上退化为 Integer，在 MySQL 上仍为 BIGINT。
BigIntType = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    pass


class UTCDateTime(TypeDecorator):
    """库内统一保存 UTC，读出时补上 UTC 时区，避免跨库时区歧义。"""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: dt.datetime | None, dialect: Any) -> dt.datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt.timezone.utc)
        return value.astimezone(dt.timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: dt.datetime | None, dialect: Any) -> dt.datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.timezone.utc)
        return value.astimezone(dt.timezone.utc)


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def create_db_engine(url: str) -> Engine:
    kwargs: dict[str, Any] = {"pool_pre_ping": True, "future": True}
    if _is_sqlite(url):
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **kwargs)

    if _is_sqlite(url):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection: Any, _record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_db_engine(settings.database_url)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False
        )
    return _session_factory


def get_db() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def create_all(engine: Engine | None = None) -> None:
    from app.models import Base as ModelBase  # noqa: F401  确保模型已注册

    ModelBase.metadata.create_all(bind=engine or get_engine())


def drop_all(engine: Engine | None = None) -> None:
    from app.models import Base as ModelBase  # noqa: F401

    ModelBase.metadata.drop_all(bind=engine or get_engine())


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)
