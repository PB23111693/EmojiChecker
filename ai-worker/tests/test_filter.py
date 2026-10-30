"""阈值过滤与事件构造用例。"""

from __future__ import annotations

import datetime as dt

import numpy as np

from ai_worker.classify import Prediction
from ai_worker.detect import FaceBox
from ai_worker.filter import EventFilter


def _face(size: int = 120) -> FaceBox:
    return FaceBox(x=10, y=10, width=size, height=size, score=0.9, landmarks=np.zeros((5, 2)))


def _prediction(emotion: str, confidence: float) -> Prediction:
    return Prediction(emotion=emotion, confidence=confidence, scores={emotion: confidence})


def test_filters_low_confidence_and_small_faces():
    """AT10 低于阈值与尺寸过小的人脸不生成事件。"""
    event_filter = EventFilter(threshold=0.6, max_faces=5, min_face_pixels=48)
    result = event_filter.apply(
        [
            (_face(120), _prediction("HAPPY", 0.81)),
            (_face(120), _prediction("SAD", 0.59)),
            (_face(30), _prediction("ANGRY", 0.95)),
        ]
    )
    assert len(result.events) == 1
    assert result.events[0].emotion == "HAPPY"
    assert result.low_confidence == 1
    assert result.too_small == 1


def test_threshold_boundary_is_inclusive():
    """AT16 置信度恰等于阈值可接收。"""
    event_filter = EventFilter(threshold=0.6, max_faces=5, min_face_pixels=48)
    result = event_filter.apply([(_face(), _prediction("NEUTRAL", 0.6))])
    assert len(result.events) == 1


def test_max_faces_per_frame():
    """AT10 超过每帧上限的人脸被丢弃并计数。"""
    event_filter = EventFilter(threshold=0.6, max_faces=2, min_face_pixels=48)
    result = event_filter.apply(
        [(_face(), _prediction("HAPPY", 0.9)) for _ in range(4)]
    )
    assert len(result.events) == 2
    assert result.overflow == 2


def test_event_shape():
    """AT09 事件包含唯一编号、UTC 时间、类别与置信度。"""
    event_filter = EventFilter(threshold=0.6, max_faces=5, min_face_pixels=48)
    now = dt.datetime(2026, 10, 29, 12, 0, tzinfo=dt.timezone.utc)
    result = event_filter.apply([(_face(), _prediction("FEARFUL", 0.7))], now=now)
    event = result.events[0]
    assert len(event.event_id) == 32
    assert event.observed_at == now
    assert event.emotion == "FEARFUL"
    assert event.confidence == 0.7
