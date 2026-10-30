"""置信度过滤与事件构造。"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field

from ai_worker.classify import Prediction
from ai_worker.detect import FaceBox


@dataclass(frozen=True)
class EmotionEvent:
    event_id: str
    observed_at: dt.datetime
    emotion: str
    confidence: float


@dataclass
class FilterResult:
    events: list[EmotionEvent] = field(default_factory=list)
    low_confidence: int = 0
    too_small: int = 0
    overflow: int = 0
    faces: int = 0


class EventFilter:
    """按课堂阈值、最小人脸尺寸与每帧上限过滤，低分结果不生成任何假数据。"""

    def __init__(self, *, threshold: float, max_faces: int, min_face_pixels: int) -> None:
        self.threshold = threshold
        self.max_faces = max_faces
        self.min_face_pixels = min_face_pixels

    def apply(
        self,
        observations: list[tuple[FaceBox, Prediction]],
        now: dt.datetime | None = None,
    ) -> FilterResult:
        observed_at = now or dt.datetime.now(dt.timezone.utc)
        result = FilterResult(faces=len(observations))
        for index, (face, prediction) in enumerate(observations):
            if index >= self.max_faces:
                result.overflow += 1
                continue
            if face.min_side < self.min_face_pixels:
                result.too_small += 1
                continue
            if prediction.confidence < self.threshold:
                result.low_confidence += 1
                continue
            result.events.append(
                EmotionEvent(
                    event_id=uuid.uuid4().hex,
                    observed_at=observed_at,
                    emotion=prediction.emotion,
                    confidence=prediction.confidence,
                )
            )
        return result
