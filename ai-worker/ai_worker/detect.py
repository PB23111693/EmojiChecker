"""人脸检测。使用 YuNet，模型与阈值见 README。"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


def _ascii_model_path(model_path: Path) -> str:
    """OpenCV 的 ONNX 导入器无法打开含非 ASCII 字符的绝对路径。

    项目目录可能包含中文，此时把模型复制到系统临时目录再加载。
    模型文件不含个人信息，复制只在本地进行。
    """
    text = str(Path(model_path).resolve())
    if all(ord(char) < 128 for char in text):
        return text
    target = Path(tempfile.gettempdir()) / f"se_emoji_{Path(model_path).name}"
    if not target.is_file() or target.stat().st_size != Path(model_path).stat().st_size:
        shutil.copyfile(model_path, target)
    return str(target)


@dataclass(frozen=True)
class FaceBox:
    x: int
    y: int
    width: int
    height: int
    score: float
    landmarks: np.ndarray  # shape (5, 2)，顺序为右眼、左眼、鼻尖、右嘴角、左嘴角

    @property
    def min_side(self) -> int:
        return min(self.width, self.height)


class FaceDetector:
    def __init__(
        self,
        model_path: Path,
        *,
        score_threshold: float = 0.6,
        nms_threshold: float = 0.3,
        top_k: int = 500,
    ) -> None:
        if not Path(model_path).is_file():
            raise FileNotFoundError(f"人脸检测模型不存在：{model_path}")
        self._detector = cv2.FaceDetectorYN.create(
            _ascii_model_path(model_path),
            "",
            (320, 320),
            score_threshold,
            nms_threshold,
            top_k,
        )

    def detect(self, frame: np.ndarray) -> list[FaceBox]:
        height, width = frame.shape[:2]
        self._detector.setInputSize((width, height))
        _, raw = self._detector.detect(frame)
        if raw is None:
            return []
        boxes: list[FaceBox] = []
        for item in raw:
            x, y, w, h = (float(value) for value in item[:4])
            x0 = max(0, int(round(x)))
            y0 = max(0, int(round(y)))
            x1 = min(width, int(round(x + w)))
            y1 = min(height, int(round(y + h)))
            if x1 <= x0 or y1 <= y0:
                continue
            landmarks = item[4:14].reshape(5, 2).astype(np.float32)
            boxes.append(
                FaceBox(
                    x=x0,
                    y=y0,
                    width=x1 - x0,
                    height=y1 - y0,
                    score=float(item[14]),
                    landmarks=landmarks,
                )
            )
        boxes.sort(key=lambda box: box.score, reverse=True)
        return boxes
