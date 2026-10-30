"""表情分类用例。模型缺失时跳过推理测试。"""

from __future__ import annotations

import numpy as np
import pytest

from ai_worker.classify import MODEL_LABELS, ExpressionClassifier, softmax
from ai_worker.config import WorkerConfig
from ai_worker.detect import FaceBox


def test_softmax_is_distribution():
    """AT10 softmax 输出非负且和为 1，最大类与 argmax 一致。"""
    logits = np.array([-1.0, 0.5, 2.0, -0.3, 1.2, 0.0, 0.1])
    probabilities = softmax(logits)
    assert np.all(probabilities >= 0)
    assert probabilities.sum() == pytest.approx(1.0)
    assert int(np.argmax(probabilities)) == 2


def test_model_label_order_matches_official_wrapper():
    """AT10 类别顺序取官方封装，不能按字母序。"""
    assert MODEL_LABELS == (
        "ANGRY",
        "DISGUST",
        "FEARFUL",
        "HAPPY",
        "NEUTRAL",
        "SAD",
        "SURPRISED",
    )


def test_predict_returns_seven_scores():
    """AT10 模型可用时，任意输入返回 7 类得分且和为 1。"""
    path = WorkerConfig().expression_model
    if not path.is_file():
        pytest.skip("模型文件未下载")
    classifier = ExpressionClassifier(path)
    frame = np.random.default_rng(20261029).integers(0, 255, (240, 240, 3), dtype=np.uint8)
    landmarks = np.array(
        [[80, 90], [160, 90], [120, 130], [90, 170], [150, 170]], dtype=np.float32
    )
    face = FaceBox(x=60, y=60, width=120, height=120, score=0.9, landmarks=landmarks)
    prediction = classifier.predict(frame, face)
    assert prediction.emotion in MODEL_LABELS
    assert 0 <= prediction.confidence <= 1
    assert len(prediction.scores) == 7
    assert sum(prediction.scores.values()) == pytest.approx(1.0, abs=1e-5)
