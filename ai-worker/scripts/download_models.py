"""下载并校验 AI 模型。模型文件不提交仓库，演示设备提前执行本脚本。

用法：
    python scripts/download_models.py
    python scripts/download_models.py --check-only
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import requests

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"

MODELS = {
    "face_detection_yunet_2026may.onnx": {
        "url": (
            "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/"
            "models/face_detection_yunet/face_detection_yunet_2026may.onnx"
        ),
        "sha256": "ebafce4e3c118d6554634be5c27ab333b4c047a9a8c3faf1d7cf93101c22f0f0",
        "license": "MIT（OpenCV Zoo，模型卡见 models/README.md）",
    },
    "facial_expression_recognition_mobilefacenet_2022july.onnx": {
        "url": (
            "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/"
            "models/facial_expression_recognition/"
            "facial_expression_recognition_mobilefacenet_2022july.onnx"
        ),
        "sha256": "4f61307602fc089ce20488a31d4e4614e3c9753a7d6c41578c854858b183e1a9",
        "license": "Apache-2.0（OpenCV Zoo）",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(name: str, path: Path) -> bool:
    expected = MODELS[name]["sha256"]
    actual = sha256(path)
    if actual != expected:
        print(f"校验失败：{name}\n  期望 {expected}\n  实际 {actual}")
        return False
    print(f"校验通过：{name}")
    return True


def download(name: str) -> bool:
    target = MODELS_DIR / name
    if target.is_file() and verify(name, target):
        return True
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"下载 {name} ...")
    response = requests.get(MODELS[name]["url"], stream=True, timeout=120)
    response.raise_for_status()
    with target.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 256):
            handle.write(chunk)
    return verify(name, target)


def main() -> int:
    parser = argparse.ArgumentParser(description="下载并校验 OpenCV Zoo 模型")
    parser.add_argument("--check-only", action="store_true", help="只校验已有文件")
    args = parser.parse_args()
    missing = 0
    for name in MODELS:
        target = MODELS_DIR / name
        if args.check_only:
            if not target.is_file():
                print(f"缺少 {name}")
                missing += 1
            elif not verify(name, target):
                missing += 1
        elif not download(name):
            missing += 1
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
