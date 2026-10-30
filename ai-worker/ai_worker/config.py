"""配置加载：YAML 文件加环境变量覆盖。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml

WORKER_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class WorkerConfig:
    api_base: str = "http://127.0.0.1:8000"
    service_key: str = ""
    device_id: str = "demo-device-01"
    session_id: int = 1
    model_version: str = "opencv-zoo-fer-2022july"
    detector_model: Path = field(
        default_factory=lambda: WORKER_DIR / "models" / "face_detection_yunet_2026may.onnx"
    )
    expression_model: Path = field(
        default_factory=lambda: WORKER_DIR
        / "models"
        / "facial_expression_recognition_mobilefacenet_2022july.onnx"
    )
    camera_index: int = 0
    video_path: Path | None = None
    replay_loop: bool = True
    sample_interval: float = 3.0
    threshold: float | None = None
    max_faces: int = 5
    min_face_pixels: int = 48
    display: bool = True
    wait_for_start: bool = True
    wait_timeout_seconds: int = 300
    log_level: str = "INFO"
    log_file: Path = field(default_factory=lambda: WORKER_DIR / "logs" / "ai-worker.log")


def _as_path(value: object, base: Path) -> Path | None:
    if value is None or value == "":
        return None
    path = Path(str(value))
    return path if path.is_absolute() else (base / path).resolve()


def load_config(path: Path | None, *, session_id: int | None = None) -> WorkerConfig:
    """读取 YAML 配置。环境变量优先于文件，命令行参数优先于两者。"""
    base = (path.parent if path else WORKER_DIR).resolve()
    raw: dict = {}
    if path and path.is_file():
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    # 默认值必须从实例读取：带 default_factory 的字段没有同名类属性。
    defaults = WorkerConfig()
    config = WorkerConfig(
        api_base=str(raw.get("api_base", defaults.api_base)).rstrip("/"),
        service_key=str(raw.get("service_key") or ""),
        device_id=str(raw.get("device_id") or defaults.device_id),
        session_id=int(raw.get("session_id", defaults.session_id)),
        model_version=str(raw.get("model_version", defaults.model_version)),
        detector_model=_as_path(raw.get("detector_model"), base) or defaults.detector_model,
        expression_model=_as_path(raw.get("expression_model"), base)
        or defaults.expression_model,
        camera_index=int(raw.get("camera_index", defaults.camera_index)),
        video_path=_as_path(raw.get("video_path"), base),
        replay_loop=bool(raw.get("replay_loop", True)),
        sample_interval=float(raw.get("sample_interval", defaults.sample_interval)),
        threshold=(None if raw.get("threshold") is None else float(raw["threshold"])),
        max_faces=int(raw.get("max_faces", defaults.max_faces)),
        min_face_pixels=int(raw.get("min_face_pixels", defaults.min_face_pixels)),
        display=bool(raw.get("display", True)),
        wait_for_start=bool(raw.get("wait_for_start", True)),
        wait_timeout_seconds=int(
            raw.get("wait_timeout_seconds", defaults.wait_timeout_seconds)
        ),
        log_level=str(raw.get("log_level", "INFO")).upper(),
        log_file=_as_path(raw.get("log_file"), base) or defaults.log_file,
    )

    overrides: dict = {}
    if os.environ.get("AI_SERVICE_KEY"):
        overrides["service_key"] = os.environ["AI_SERVICE_KEY"].strip()
    if os.environ.get("AI_DEVICE_ID"):
        overrides["device_id"] = os.environ["AI_DEVICE_ID"].strip()
    if os.environ.get("AI_API_BASE"):
        overrides["api_base"] = os.environ["AI_API_BASE"].strip().rstrip("/")
    if session_id is not None:
        overrides["session_id"] = session_id
    if overrides:
        config = replace(config, **overrides)

    if config.sample_interval <= 0:
        raise ValueError("sample_interval 必须大于 0")
    if config.max_faces <= 0:
        raise ValueError("max_faces 必须大于 0")
    if not config.service_key:
        raise ValueError("未配置 service_key，请设置配置文件或环境变量 AI_SERVICE_KEY")
    return config
