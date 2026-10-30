"""表情分类。读取 ONNX 原始 7 维 logits，softmax 后取最大类得分作为置信度。

已实测：opencv_zoo 的 facial_expression_recognition_mobilefacenet_2022july.onnx
输出名为 label、形状 (1, 7)，数值为 logits（随机输入下含负值且和不为 1），
因此必须在此处执行 softmax，不能把 argmax 结果当作置信度。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from ai_worker.detect import FaceBox

logger = logging.getLogger(__name__)

# 模型输出顺序，取自 OpenCV Zoo 官方封装 facial_fer_model.py 的 getDesc。
# 该顺序与字母序不同，不能按字母序映射。
MODEL_LABELS = (
    "ANGRY",
    "DISGUST",
    "FEARFUL",
    "HAPPY",
    "NEUTRAL",
    "SAD",
    "SURPRISED",
)

# 官方对齐使用的 112x112 标准五点位置。
_STANDARD_LANDMARKS = np.array(
    [
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ],
    dtype=np.float32,
)
_INPUT_SIZE = 112


@dataclass(frozen=True)
class Prediction:
    emotion: str
    confidence: float
    scores: dict[str, float]


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits)
    exponent = np.exp(shifted)
    return exponent / np.sum(exponent)


class ExpressionClassifier:
    def __init__(self, model_path: Path) -> None:
        if not Path(model_path).is_file():
            raise FileNotFoundError(f"表情模型不存在：{model_path}")
        options = ort.SessionOptions()
        options.log_severity_level = 3
        self._session = ort.InferenceSession(
            str(model_path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self._input_name = self._session.get_inputs()[0].name
        self._output_name = self._session.get_outputs()[0].name
        self._warmup()

    def _warmup(self) -> None:
        dummy = np.zeros((1, 3, _INPUT_SIZE, _INPUT_SIZE), dtype=np.float32)
        self._session.run([self._output_name], {self._input_name: dummy})

    def _align(self, frame: np.ndarray, face: FaceBox) -> np.ndarray:
        matrix, _ = cv2.estimateAffinePartial2D(
            face.landmarks, _STANDARD_LANDMARKS, method=cv2.LMEDS
        )
        if matrix is None:
            # 关键点异常时退化为带边距的裁剪，保证流程不中断。
            margin_x = int(face.width * 0.2)
            margin_y = int(face.height * 0.2)
            x0 = max(0, face.x - margin_x)
            y0 = max(0, face.y - margin_y)
            x1 = min(frame.shape[1], face.x + face.width + margin_x)
            y1 = min(frame.shape[0], face.y + face.height + margin_y)
            crop = frame[y0:y1, x0:x1]
            return cv2.resize(crop, (_INPUT_SIZE, _INPUT_SIZE))
        return cv2.warpAffine(frame, matrix, (_INPUT_SIZE, _INPUT_SIZE))

    def _preprocess(self, aligned_bgr: np.ndarray) -> np.ndarray:
        rgb = cv2.cvtColor(aligned_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        rgb = (rgb - 0.5) / 0.5
        return np.transpose(rgb, (2, 0, 1))[None, ...].astype(np.float32)

    def predict(self, frame: np.ndarray, face: FaceBox) -> Prediction:
        aligned = self._align(frame, face)
        blob = self._preprocess(aligned)
        logits = self._session.run([self._output_name], {self._input_name: blob})[0][0]
        probabilities = softmax(np.asarray(logits, dtype=np.float64))
        index = int(np.argmax(probabilities))
        scores = {
            label: round(float(probabilities[position]), 6)
            for position, label in enumerate(MODEL_LABELS)
        }
        return Prediction(
            emotion=MODEL_LABELS[index],
            confidence=round(float(probabilities[index]), 6),
            scores=scores,
        )
