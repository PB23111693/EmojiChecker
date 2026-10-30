"""视频输入。摄像头与回放文件共用同一读取接口。"""

from __future__ import annotations

import logging
import sys
from abc import ABC, abstractmethod
from pathlib import Path

import cv2
import numpy as np

from ai_worker.config import WorkerConfig

logger = logging.getLogger(__name__)


class FrameSource(ABC):
    is_replay: bool = False

    @abstractmethod
    def read(self) -> tuple[bool, np.ndarray | None]:
        """返回 (是否成功, BGR 帧)。帧只在内存中使用，不写盘。"""

    @abstractmethod
    def release(self) -> None:
        """释放采集设备或文件句柄。"""

    @property
    @abstractmethod
    def description(self) -> str:
        """写入日志的输入描述。"""


class CameraSource(FrameSource):
    def __init__(self, index: int, width: int = 640, height: int = 480) -> None:
        self._index = index
        api = cv2.CAP_DSHOW if sys.platform.startswith("win") else 0
        self._capture = cv2.VideoCapture(index, api)
        if not self._capture.isOpened() and api:
            self._capture.release()
            self._capture = cv2.VideoCapture(index)
        if not self._capture.isOpened():
            raise RuntimeError(f"无法打开摄像头 {index}，请检查设备占用与权限")
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def read(self) -> tuple[bool, np.ndarray | None]:
        return self._capture.read()

    def release(self) -> None:
        self._capture.release()

    @property
    def description(self) -> str:
        return f"camera:{self._index}"


class VideoFileSource(FrameSource):
    """回放输入。使用回放时必须在日志与界面中标注，不得冒充现场采集。"""

    is_replay = True

    def __init__(self, path: Path, loop: bool = True) -> None:
        if not path.is_file():
            raise FileNotFoundError(f"回放文件不存在：{path}")
        self._path = path
        self._loop = loop
        self._capture = cv2.VideoCapture(str(path))
        if not self._capture.isOpened():
            raise RuntimeError(f"无法打开回放文件：{path}")

    def read(self) -> tuple[bool, np.ndarray | None]:
        ok, frame = self._capture.read()
        if not ok and self._loop:
            self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self._capture.read()
        return ok, frame

    def release(self) -> None:
        self._capture.release()

    @property
    def description(self) -> str:
        return f"replay:{self._path.name}"


def open_source(config: WorkerConfig) -> FrameSource:
    if config.video_path is not None:
        logger.warning("使用回放输入 %s，本次结果不代表现场采集", config.video_path)
        return VideoFileSource(config.video_path, loop=config.replay_loop)
    return CameraSource(config.camera_index)
