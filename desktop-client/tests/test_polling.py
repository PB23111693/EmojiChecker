"""桌面客户端结果轮询的容错用例。"""

from __future__ import annotations

import queue
import tkinter as tk

import client


def test_polling_continues_after_destroyed_widget_callback():
    """F04 迟到回调访问已销毁控件时，轮询链仍继续执行。"""
    app = object.__new__(client.DesktopApp)
    app._results = queue.Queue()
    scheduled: list = []
    app.after = lambda _delay, callback: scheduled.append(callback)
    app.winfo_exists = lambda: True

    called: list = []

    def stale_callback(_value):
        raise tk.TclError("invalid command name")

    app._results.put((stale_callback, None, None, None))
    app._results.put((lambda value: called.append(value), None, "ok", None))

    app._poll_results()

    assert called == ["ok"]
    assert len(scheduled) == 1
