"""演示课堂刷新必须保留 UTC 存储，并明确输出北京时间。"""

import datetime as dt

from app.models import ClassSession, EmojiRecord, SessionStatus, User
from app.services.catalog_service import CatalogService
from scripts import seed_demo


def test_refresh_preserves_utc_and_prints_beijing_time(client, db, monkeypatch, capsys):
    """北京时间跨日时，refresh 输出、UTC 持久化与课堂状态仍然一致。"""
    now = dt.datetime(2026, 10, 31, 16, 5, tzinfo=dt.timezone.utc)
    monkeypatch.setattr(seed_demo, "utcnow", lambda: now)
    seed_demo.seed()
    counts = (db.query(User).count(), db.query(EmojiRecord).count())
    capsys.readouterr()

    seed_demo.refresh_demo_times()
    output = capsys.readouterr().out
    db.expire_all()
    ongoing = db.get(ClassSession, 1)

    assert ongoing.start_at == now - dt.timedelta(minutes=15)
    assert ongoing.end_at == now + dt.timedelta(minutes=45)
    assert ongoing.start_at.utcoffset() == dt.timedelta(0)
    assert (db.query(User).count(), db.query(EmojiRecord).count()) == counts
    response = CatalogService(db)._to_out(ongoing, now=now)
    assert response.status == SessionStatus.ONGOING
    assert '"start_at":"2026-10-31T15:50:00Z"' in response.model_dump_json()
    assert "北京时间 UTC+08:00" in output
    assert "2026-10-31 23:50 至 2026-11-01 00:50" in output
