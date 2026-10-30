"""采样主循环：取帧、检测、分类、过滤、上传、显示与退出。"""

from __future__ import annotations

import datetime as dt
import logging
import time

import cv2
import requests

from ai_worker.api import ApiClient, ApiError, AuthError
from ai_worker.capture import FrameSource, open_source
from ai_worker.classify import ExpressionClassifier
from ai_worker.config import WorkerConfig
from ai_worker.detect import FaceDetector
from ai_worker.filter import EventFilter
from ai_worker.uploader import Uploader

logger = logging.getLogger(__name__)

CONTEXT_REFRESH_SECONDS = 30


class Runner:
    def __init__(self, config: WorkerConfig, api: ApiClient, context: dict) -> None:
        self.config = config
        self.api = api
        self.context = context
        self.threshold = (
            config.threshold if config.threshold is not None else float(context["ai_threshold"])
        )
        self.detector = FaceDetector(config.detector_model)
        self.classifier = ExpressionClassifier(config.expression_model)
        self.source: FrameSource = open_source(config)
        self.filter = EventFilter(
            threshold=self.threshold,
            max_faces=config.max_faces,
            min_face_pixels=config.min_face_pixels,
        )
        self.uploader = Uploader(
            api,
            session_id=config.session_id,
            device_id=config.device_id,
            model_version=config.model_version,
        )
        self.frames = 0
        self.faces = 0
        self.no_face_frames = 0
        self.small_faces = 0
        self.low_confidence = 0
        self.overflow = 0
        self.events = 0

    def _status(self) -> str:
        return str(self.context.get("status", ""))

    def run(self, *, once: bool = False, display: bool = True) -> None:
        logger.info(
            "开始采样 session=%s device=%s input=%s threshold=%.2f interval=%.1fs%s",
            self.config.session_id,
            self.config.device_id,
            self.source.description,
            self.threshold,
            self.config.sample_interval,
            "（回放输入）" if self.source.is_replay else "",
        )
        last_context = time.monotonic()
        try:
            while True:
                started = time.monotonic()
                ok, frame = self.source.read()
                if not ok or frame is None:
                    logger.warning("输入结束或读取失败，停止采样")
                    break

                self.frames += 1
                now = dt.datetime.now(dt.timezone.utc)
                faces = self.detector.detect(frame)
                self.faces += len(faces)
                if not faces:
                    self.no_face_frames += 1

                observations = []
                for face in faces[: self.config.max_faces]:
                    prediction = self.classifier.predict(frame, face)
                    observations.append((face, prediction))
                if len(faces) > self.config.max_faces:
                    self.overflow += len(faces) - self.config.max_faces

                result = self.filter.apply(observations, now=now)
                self.small_faces += result.too_small
                self.low_confidence += result.low_confidence
                self.events += len(result.events)
                self.uploader.enqueue(result.events)
                try:
                    self.uploader.flush()
                except AuthError as exc:
                    logger.error("AI 服务密钥或设备配置错误，停止上传：%s", exc)
                    break

                if display:
                    self._draw(frame, observations, result.events)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        logger.info("用户按键退出")
                        break

                if once:
                    break

                if time.monotonic() - last_context >= CONTEXT_REFRESH_SECONDS:
                    if not self._refresh_context():
                        break
                    last_context = time.monotonic()

                elapsed = time.monotonic() - started
                time.sleep(max(0.0, self.config.sample_interval - elapsed))
        finally:
            self.source.release()
            if display:
                cv2.destroyAllWindows()
            logger.info(
                "采样结束 frames=%s faces=%s no_face_frames=%s small_faces=%s "
                "low_confidence=%s overflow=%s events=%s %s",
                self.frames,
                self.faces,
                self.no_face_frames,
                self.small_faces,
                self.low_confidence,
                self.overflow,
                self.events,
                self.uploader.stats.summary(),
            )

    def _refresh_context(self) -> bool:
        """刷新课堂配置。临时断网沿用上次状态，鉴权或课堂消失才停止。

        返回 False 表示应结束采集；返回 True 表示可以继续，即使本次刷新失败。
        """
        try:
            self.context = self.api.context(self.config.session_id, self.config.device_id)
        except AuthError as exc:
            logger.error("刷新课堂配置时认证失败，停止采集：%s", exc)
            return False
        except ApiError as exc:
            if 400 <= exc.status_code < 500:
                logger.error("刷新课堂配置被拒绝（%s），停止采集", exc)
                return False
            logger.warning("刷新课堂配置失败（%s），沿用上次状态继续采样", exc)
            return True
        except requests.RequestException as exc:
            logger.warning(
                "刷新课堂配置时网络异常（%s），沿用上次状态继续采样", exc.__class__.__name__
            )
            return True

        if self._status() != "ONGOING":
            logger.info("课堂状态变为 %s，停止采样", self._status())
            return False
        return True

    def _draw(self, frame, observations, events) -> None:
        accepted = {event.emotion for event in events}
        for face, prediction in observations:
            color = (46, 160, 67) if prediction.emotion in accepted else (120, 120, 120)
            cv2.rectangle(
                frame,
                (face.x, face.y),
                (face.x + face.width, face.y + face.height),
                color,
                2,
            )
            label = f"{prediction.emotion} {prediction.confidence:.2f}"
            cv2.putText(
                frame,
                label,
                (face.x, max(16, face.y - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
                cv2.LINE_AA,
            )
        banner = f"session {self.config.session_id}  threshold {self.threshold:.2f}"
        if self.source.is_replay:
            banner += "  [REPLAY INPUT]"
            cv2.putText(
                frame,
                "REPLAY INPUT",
                (12, 26),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
                cv2.LINE_AA,
            )
        cv2.putText(
            frame,
            banner,
            (12, frame.shape[0] - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        cv2.imshow("SE Emoji Checker - AI Worker", frame)
