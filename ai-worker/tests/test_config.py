"""配置加载与命令行参数用例。"""

from __future__ import annotations

import pytest

from ai_worker import cli
from ai_worker.config import WorkerConfig, load_config


def test_load_config_without_file_uses_instance_defaults(monkeypatch):
    """A02 无配置文件时使用实例默认值，不再访问不存在的 dataclass 类属性。"""
    monkeypatch.setenv("AI_SERVICE_KEY", "test-key")
    config = load_config(None)
    defaults = WorkerConfig()
    assert config.detector_model == defaults.detector_model
    assert config.expression_model == defaults.expression_model
    assert config.log_file == defaults.log_file
    assert config.session_id == defaults.session_id


def test_load_config_minimal_file(monkeypatch, tmp_path):
    """A02 最小 YAML 只写一个字段，其余字段回落到默认值。"""
    monkeypatch.setenv("AI_SERVICE_KEY", "test-key")
    path = tmp_path / "config.yaml"
    path.write_text("session_id: 7\n", encoding="utf-8")
    config = load_config(path)
    assert config.session_id == 7
    assert config.sample_interval == WorkerConfig().sample_interval


def test_no_wait_flag_is_passed_to_wait(monkeypatch):
    """A03 --no-wait 必须关闭等待课堂开始。"""
    captured: dict = {}
    config = WorkerConfig(service_key="test-key", wait_for_start=True)

    class DummyApi:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def close(self) -> None:
            pass

    def fake_wait(api, cfg, *, wait):
        captured["wait"] = wait
        raise SystemExit(0)

    monkeypatch.setattr(cli, "load_config", lambda *args, **kwargs: config)
    monkeypatch.setattr(cli, "setup_logging", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "ApiClient", DummyApi)
    monkeypatch.setattr(cli, "wait_for_ongoing", fake_wait)

    with pytest.raises(SystemExit):
        cli.main(["--config", "ignored.yaml", "--no-wait"])
    assert captured["wait"] is False
