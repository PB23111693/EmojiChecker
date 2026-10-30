"""命令行入口。"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import replace
from pathlib import Path

import requests

from ai_worker.api import ApiClient, ApiError, AuthError
from ai_worker.config import WORKER_DIR, load_config
from ai_worker.runner import Runner

logger = logging.getLogger(__name__)


def setup_logging(level: str, log_file: Path | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=handlers,
    )
    logging.getLogger("onnxruntime").setLevel(logging.ERROR)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="课堂情绪检查器 AI 推理进程")
    parser.add_argument(
        "--config",
        type=Path,
        default=WORKER_DIR / "config.yaml" if (WORKER_DIR / "config.yaml").is_file() else None,
        help="YAML 配置文件，默认使用本目录 config.yaml（存在时）",
    )
    parser.add_argument("--session-id", type=int, help="覆盖配置中的课堂 ID")
    parser.add_argument("--camera", type=int, help="覆盖摄像头序号")
    parser.add_argument("--video", type=str, help="使用回放视频，覆盖摄像头输入")
    parser.add_argument("--threshold", type=float, help="覆盖课堂置信度阈值")
    parser.add_argument("--interval", type=float, help="覆盖采样间隔（秒）")
    parser.add_argument("--once", action="store_true", help="只采样一帧后退出，用于联调")
    parser.add_argument("--no-display", action="store_true", help="不显示预览窗口")
    parser.add_argument("--no-wait", action="store_true", help="课堂未开始时立即退出")
    parser.add_argument("--log-level", default=None, help="DEBUG/INFO/WARNING/ERROR")
    return parser


def wait_for_ongoing(api: ApiClient, config, *, wait: bool) -> dict:
    deadline = time.monotonic() + config.wait_timeout_seconds
    while True:
        context = api.context(config.session_id, config.device_id)
        status = str(context.get("status", ""))
        if status == "ONGOING":
            return context
        if status in {"ENDED", "CANCELLED"}:
            raise SystemExit(f"课堂状态为 {status}，不能开始采样")
        if not wait:
            raise SystemExit(f"课堂状态为 {status}，未开始采样")
        if time.monotonic() >= deadline:
            raise SystemExit(f"等待课堂开始超时（{config.wait_timeout_seconds} 秒）")
        logger.info("课堂状态为 %s，10 秒后重试", status)
        time.sleep(10)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config, session_id=args.session_id)
    except (ValueError, OSError) as exc:
        print(f"配置错误：{exc}", file=sys.stderr)
        return 2

    overrides = {}
    if args.camera is not None:
        overrides["camera_index"] = args.camera
    if args.video:
        overrides["video_path"] = Path(args.video).resolve()
    if args.threshold is not None:
        if not 0 <= args.threshold <= 1:
            print("阈值必须在 0 至 1 之间", file=sys.stderr)
            return 2
        overrides["threshold"] = args.threshold
    if args.interval is not None:
        overrides["sample_interval"] = args.interval
    if args.no_display:
        overrides["display"] = False
    if args.log_level:
        overrides["log_level"] = args.log_level.upper()
    if overrides:
        config = replace(config, **overrides)

    setup_logging(config.log_level, config.log_file)
    logger.info("配置文件：%s", args.config or "内置默认值")

    api = ApiClient(config.api_base, config.service_key)
    try:
        context = wait_for_ongoing(
            api,
            config,
            wait=config.wait_for_start and not args.once and not args.no_wait,
        )
        logger.info(
            "课堂 %s %s/%s 阈值 %.2f",
            context["session_id"],
            context["course_name"],
            context["class_name"],
            context["ai_threshold"],
        )
        runner = Runner(config, api, context)
        runner.run(once=args.once, display=config.display)
        return 0
    except AuthError as exc:
        logger.error("认证失败：%s（检查 AI_SERVICE_KEY 与 AI_DEVICE_ID）", exc)
        return 3
    except ApiError as exc:
        logger.error("后端返回错误：%s", exc)
        return 4
    except requests.RequestException as exc:
        logger.error("无法连接后端 %s：%s", config.api_base, exc)
        return 4
    except KeyboardInterrupt:
        logger.info("收到中断信号，已停止")
        return 0
    except (FileNotFoundError, RuntimeError) as exc:
        logger.error("启动失败：%s", exc)
        return 5
    finally:
        api.close()
