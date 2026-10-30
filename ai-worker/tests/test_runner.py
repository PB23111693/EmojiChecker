"""Runner 配置刷新容错用例。"""

from __future__ import annotations

from types import SimpleNamespace

import requests

from ai_worker.api import ApiError, AuthError
from ai_worker.runner import Runner


def _runner(api) -> Runner:
    runner = object.__new__(Runner)
    runner.config = SimpleNamespace(session_id=1, device_id="test-device")
    runner.api = api
    runner.context = {"status": "ONGOING"}
    return runner


class _NetworkDown:
    def context(self, *_args):
        raise requests.ConnectionError("down")


class _AuthBad:
    def context(self, *_args):
        raise AuthError(401, "bad key")


class _ServerError:
    def context(self, *_args):
        raise ApiError(503, "busy")


class _NotFound:
    def context(self, *_args):
        raise ApiError(404, "gone")


def test_refresh_context_survives_network_failure():
    """A01 配置刷新遇到断网时继续采样，不终止进程。"""
    runner = _runner(_NetworkDown())
    assert runner._refresh_context() is True
    assert runner._status() == "ONGOING"


def test_refresh_context_survives_server_error():
    runner = _runner(_ServerError())
    assert runner._refresh_context() is True


def test_refresh_context_stops_on_auth_failure():
    runner = _runner(_AuthBad())
    assert runner._refresh_context() is False


def test_refresh_context_stops_when_session_missing():
    runner = _runner(_NotFound())
    assert runner._refresh_context() is False
