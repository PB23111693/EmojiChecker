"""课堂情绪检查器桌面客户端。

使用 Python 标准库 tkinter 与 urllib 实现，覆盖登录、选择课堂、提交表情、
查看个人历史与修改密码五条流程，与 Web 端共用同一套 REST 接口，构成 C/S 通道。

用法：
    python client.py
    python client.py --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import queue
import threading
import tkinter as tk
import traceback
import uuid
from tkinter import messagebox, ttk
from typing import Any, Callable
from urllib import error, request

EMOTIONS = [
    ("HAPPY", "😄", "开心"),
    ("NEUTRAL", "😐", "平静"),
    ("SAD", "😢", "低落"),
    ("ANGRY", "😠", "生气"),
    ("SURPRISED", "😮", "惊讶"),
    ("FEARFUL", "😨", "害怕"),
    ("DISGUST", "🤢", "厌恶"),
]
EMOTION_LABEL = {code: f"{icon} {label}" for code, icon, label in EMOTIONS}
STATUS_LABEL = {
    "PENDING": "未开始",
    "ONGOING": "进行中",
    "ENDED": "已结束",
    "CANCELLED": "已取消",
}


class ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        self.status = status
        self.message = message
        super().__init__(message)


def format_time(value: str) -> str:
    try:
        moment = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return moment.astimezone().strftime("%m-%d %H:%M")
    except (ValueError, AttributeError):
        return str(value)


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token: str | None = None
        self.user: dict[str, Any] | None = None

    def _request(self, method: str, path: str, payload: dict | None = None) -> Any:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with request.urlopen(req, timeout=15) as response:
                body = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            try:
                body = json.loads(exc.read().decode("utf-8"))
                message = body.get("message") or "请求失败"
            except (ValueError, UnicodeDecodeError):
                message = f"HTTP {exc.code}"
            raise ApiError(exc.code, message) from exc
        except error.URLError as exc:
            raise ApiError(0, f"无法连接服务器：{exc.reason}") from exc
        if body.get("code") != 0:
            raise ApiError(400, body.get("message") or "请求失败")
        return body.get("data")

    def login(self, username: str, password: str) -> dict:
        data = self._request(
            "POST", "/api/v1/auth/login", {"username": username, "password": password}
        )
        self.token = data["access_token"]
        self.user = data["user"]
        return data

    def sessions(self) -> dict:
        return self._request("GET", "/api/v1/sessions?page=1&page_size=100")

    def submit(self, session_id: int, emotion: str) -> dict:
        return self._request(
            "POST",
            "/api/v1/emoji",
            {"event_id": uuid.uuid4().hex, "session_id": session_id, "emotion": emotion},
        )

    def history(self, page: int, page_size: int = 20) -> dict:
        return self._request(
            "GET", f"/api/v1/emoji/history?page={page}&page_size={page_size}"
        )

    def change_password(self, old_password: str, new_password: str) -> None:
        self._request(
            "PUT",
            "/api/v1/auth/password",
            {"old_password": old_password, "new_password": new_password},
        )


class LoginFrame(ttk.Frame):
    def __init__(self, master: "DesktopApp") -> None:
        super().__init__(master, padding=24)
        self.master_app = master
        ttk.Label(self, text="课堂情绪检查器", font=("Microsoft YaHei UI", 18, "bold")).pack(
            pady=(10, 4)
        )
        ttk.Label(self, text="桌面客户端 · 学生端", foreground="#5b6b66").pack(pady=(0, 18))

        form = ttk.Frame(self)
        form.pack(fill="x", padx=30)
        self.username = tk.StringVar(value="stu2021001")
        self.password = tk.StringVar()
        self._field(form, "用户名", self.username, 0)
        ttk.Label(form, text="密码").grid(row=1, column=0, sticky="w", pady=6)
        self.password_entry = ttk.Entry(form, textvariable=self.password, show="*", width=30)
        self.password_entry.grid(row=1, column=1, sticky="we", pady=6)
        form.columnconfigure(1, weight=1)

        ttk.Button(self, text="登录", command=self.submit).pack(fill="x", padx=30, pady=(20, 6))
        ttk.Button(self, text="退出", command=master.destroy).pack(fill="x", padx=30)
        self.status = ttk.Label(self, text="", foreground="#b3261e")
        self.status.pack(pady=10)
        self.password_entry.bind("<Return>", lambda _: self.submit())

    def _field(self, parent, label: str, variable: tk.StringVar, row: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=6)
        ttk.Entry(parent, textvariable=variable, width=30).grid(
            row=row, column=1, sticky="we", pady=6
        )

    def submit(self) -> None:
        username = self.username.get().strip()
        password = self.password.get()
        if not username or not password:
            self.status.configure(text="请输入用户名与密码")
            return
        self.status.configure(text="正在登录……")
        self.master_app.run_async(
            lambda: self.master_app.api.login(username, password),
            self._done,
            self._failed,
        )

    def _done(self, _data: dict) -> None:
        self.status.configure(text="")
        self.master_app.show_main()

    def _failed(self, exc: ApiError) -> None:
        self.status.configure(text=exc.message)


class MainFrame(ttk.Frame):
    def __init__(self, master: "DesktopApp") -> None:
        super().__init__(master, padding=12)
        self.master_app = master
        self.selected_session: dict | None = None
        self._session_map: dict[str, dict] = {}
        self.history_page = 1
        self.history_pages = 1

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 8))
        user = master.api.user or {}
        ttk.Label(
            header,
            text=f"{user.get('username', '')} · {user.get('role', '')}",
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(side="left")
        ttk.Button(header, text="退出登录", command=master.logout).pack(side="right")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        self._build_sessions()
        self._build_feedback()
        self._build_history()
        self._build_account()
        self.status = ttk.Label(self, text="", foreground="#5b6b66")
        self.status.pack(fill="x", pady=(6, 0))

    # ---------- 课堂 ----------
    def _build_sessions(self) -> None:
        frame = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(frame, text="我的课堂")
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x", pady=(0, 6))
        ttk.Button(toolbar, text="刷新", command=self.load_sessions).pack(side="left")
        ttk.Label(toolbar, text="仅进行中的课堂可提交反馈", foreground="#5b6b66").pack(
            side="left", padx=10
        )

        columns = ("course", "class", "room", "start", "end", "status")
        self.session_tree = ttk.Treeview(frame, columns=columns, show="headings", height=12)
        for key, title, width in (
            ("course", "课程", 160),
            ("class", "班级", 110),
            ("room", "教室", 100),
            ("start", "开始", 110),
            ("end", "结束", 110),
            ("status", "状态", 80),
        ):
            self.session_tree.heading(key, text=title)
            self.session_tree.column(key, width=width, anchor="center")
        self.session_tree.pack(fill="both", expand=True)
        self.session_tree.bind("<Double-1>", lambda _: self.open_feedback())

        ttk.Button(frame, text="进入反馈", command=self.open_feedback).pack(pady=6)

    def load_sessions(self) -> None:
        self.status.configure(text="正在加载课堂……")
        self.master_app.run_async(self.master_app.api.sessions, self._sessions_done, self._failed)

    def _sessions_done(self, data: dict) -> None:
        self.session_tree.delete(*self.session_tree.get_children())
        self._session_map = {}
        for item in data.get("items", []):
            iid = str(item["id"])
            self._session_map[iid] = item
            self.session_tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    item["course_name"],
                    item["class_name"],
                    item.get("room") or "-",
                    format_time(item["start_at"]),
                    format_time(item["end_at"]),
                    STATUS_LABEL.get(item["status"], item["status"]),
                ),
            )
        self.status.configure(text=f"共 {len(data.get('items', []))} 节课堂")

    def open_feedback(self) -> None:
        selection = self.session_tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选择一节课堂")
            return
        session = self._session_map[selection[0]]
        if session["status"] != "ONGOING":
            messagebox.showwarning("提示", "只有进行中的课堂可以提交反馈")
            return
        if (self.master_app.api.user or {}).get("role") != "STUDENT":
            messagebox.showwarning("提示", "桌面客户端面向学生提交反馈")
            return
        self.selected_session = session
        self.feedback_title.configure(
            text=f"{session['course_name']} · {session['class_name']} · {format_time(session['start_at'])}"
        )
        self.feedback_result.configure(text="")
        self.notebook.select(1)

    # ---------- 反馈 ----------
    def _build_feedback(self) -> None:
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text="提交反馈")
        self.feedback_title = ttk.Label(
            frame, text="请先在“我的课堂”选择进行中的课堂", font=("Microsoft YaHei UI", 11, "bold")
        )
        self.feedback_title.pack(pady=(4, 12))

        grid = ttk.Frame(frame)
        grid.pack()
        self.emotion_buttons = []
        for index, (code, icon, label) in enumerate(EMOTIONS):
            button = ttk.Button(
                grid,
                text=f"{icon}\n{label}",
                width=10,
                command=lambda value=code: self.submit(value),
            )
            button.grid(row=index // 4, column=index % 4, padx=6, pady=6, ipady=8)
            self.emotion_buttons.append(button)

        self.feedback_result = ttk.Label(frame, text="", font=("Microsoft YaHei UI", 10))
        self.feedback_result.pack(pady=16)
        ttk.Label(
            frame,
            text="同一课堂每 30 秒只能提交一次；网络失败时请勿重复点击，等待提示后再试。",
            foreground="#5b6b66",
        ).pack()

    def submit(self, emotion: str) -> None:
        if self.selected_session is None:
            messagebox.showwarning("提示", "请先在“我的课堂”选择进行中的课堂")
            return
        session_id = self.selected_session["id"]
        for button in self.emotion_buttons:
            button.state(["disabled"])
        self.feedback_result.configure(text="正在提交……")
        self.master_app.run_async(
            lambda: self.master_app.api.submit(session_id, emotion),
            self._submit_done,
            self._submit_failed,
        )

    def _submit_done(self, data: dict) -> None:
        for button in self.emotion_buttons:
            button.state(["!disabled"])
        if data.get("duplicate"):
            self.feedback_result.configure(text="该次提交已处理，未重复写入")
        else:
            moment = format_time(data.get("observed_at", ""))
            self.feedback_result.configure(text=f"提交成功 · {moment}")

    def _submit_failed(self, exc: ApiError) -> None:
        for button in self.emotion_buttons:
            button.state(["!disabled"])
        self.feedback_result.configure(text=exc.message)

    # ---------- 历史 ----------
    def _build_history(self) -> None:
        frame = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(frame, text="我的记录")
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x", pady=(0, 6))
        ttk.Button(toolbar, text="刷新", command=self.load_history).pack(side="left")
        self.page_label = ttk.Label(toolbar, text="第 1 / 1 页")
        self.page_label.pack(side="left", padx=10)
        ttk.Button(toolbar, text="上一页", command=lambda: self.turn_page(-1)).pack(side="right")
        ttk.Button(toolbar, text="下一页", command=lambda: self.turn_page(1)).pack(
            side="right", padx=6
        )

        columns = ("time", "course", "class", "emotion", "source")
        self.history_tree = ttk.Treeview(frame, columns=columns, show="headings", height=14)
        for key, title, width in (
            ("time", "时间", 150),
            ("course", "课程", 170),
            ("class", "班级", 110),
            ("emotion", "表情", 110),
            ("source", "来源", 80),
        ):
            self.history_tree.heading(key, text=title)
            self.history_tree.column(key, width=width, anchor="center")
        self.history_tree.pack(fill="both", expand=True)

    def load_history(self) -> None:
        self.master_app.run_async(
            lambda: self.master_app.api.history(self.history_page), self._history_done, self._failed
        )

    def _history_done(self, data: dict) -> None:
        self.history_tree.delete(*self.history_tree.get_children())
        for item in data.get("items", []):
            self.history_tree.insert(
                "",
                "end",
                values=(
                    format_time(item["observed_at"]),
                    item["course_name"],
                    item["class_name"],
                    EMOTION_LABEL.get(item["emotion"], item["emotion"]),
                    "手动" if item["source"] == "MANUAL" else "AI",
                ),
            )
        total = int(data.get("total", 0))
        size = int(data.get("page_size", 20)) or 20
        self.history_pages = max(1, (total + size - 1) // size)
        self.page_label.configure(text=f"第 {self.history_page} / {self.history_pages} 页，共 {total} 条")

    def turn_page(self, delta: int) -> None:
        target = self.history_page + delta
        if 1 <= target <= self.history_pages:
            self.history_page = target
            self.load_history()

    # ---------- 账号 ----------
    def _build_account(self) -> None:
        frame = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(frame, text="修改密码")
        self.old_password = tk.StringVar()
        self.new_password = tk.StringVar()
        self.confirm_password = tk.StringVar()
        for row, (label, variable) in enumerate(
            (
                ("原密码", self.old_password),
                ("新密码", self.new_password),
                ("确认新密码", self.confirm_password),
            )
        ):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=8)
            ttk.Entry(frame, textvariable=variable, show="*", width=32).grid(
                row=row, column=1, sticky="we", pady=8
            )
        frame.columnconfigure(1, weight=1)
        ttk.Button(frame, text="修改密码", command=self.change_password).grid(
            row=3, column=0, columnspan=2, sticky="we", pady=14
        )
        self.account_status = ttk.Label(frame, text="")
        self.account_status.grid(row=4, column=0, columnspan=2)

    def change_password(self) -> None:
        if self.new_password.get() != self.confirm_password.get():
            self.account_status.configure(text="两次输入的新密码不一致")
            return
        self.master_app.run_async(
            lambda: self.master_app.api.change_password(
                self.old_password.get(), self.new_password.get()
            ),
            self._password_done,
            lambda exc: self.account_status.configure(text=exc.message),
        )

    def _password_done(self, _data: None) -> None:
        messagebox.showinfo("完成", "密码已修改，请重新登录")
        self.master_app.logout()

    def _failed(self, exc: ApiError) -> None:
        self.status.configure(text=exc.message)
        if exc.status == 401:
            messagebox.showwarning("登录失效", "登录已过期，请重新登录")
            self.master_app.logout()

    def refresh(self) -> None:
        self.load_sessions()
        self.load_history()


class DesktopApp(tk.Tk):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.title("课堂情绪检查器 · 桌面客户端")
        self.geometry("860x620")
        self.minsize(760, 540)
        self.api = ApiClient(base_url)
        self.current: ttk.Frame | None = None
        # 后台线程不直接操作 Tk 控件，结果放入队列，由主线程轮询执行回调。
        self._results: queue.Queue = queue.Queue()
        self._show(LoginFrame(self))
        self.after(50, self._poll_results)

    def _show(self, frame: ttk.Frame) -> None:
        if self.current is not None:
            self.current.destroy()
        self.current = frame
        frame.pack(fill="both", expand=True)

    def show_main(self) -> None:
        main = MainFrame(self)
        self._show(main)
        main.refresh()

    def logout(self) -> None:
        self.api.token = None
        self.api.user = None
        self._show(LoginFrame(self))

    def _poll_results(self) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        try:
            while True:
                on_success, on_error, result, failure = self._results.get_nowait()
                try:
                    if failure is None:
                        on_success(result)
                    elif on_error is not None:
                        on_error(failure)
                    else:
                        messagebox.showerror("请求失败", failure.message)
                except tk.TclError:
                    # 迟到回调对应的界面已被销毁（退出登录或切换页面），忽略即可。
                    continue
                except Exception:  # noqa: BLE001 单个回调失败不应中断后续结果
                    traceback.print_exc()
        except queue.Empty:
            pass
        finally:
            # 无论本轮是否发生异常都继续轮询，避免一次 TclError 让界面永久失去响应。
            try:
                self.after(50, self._poll_results)
            except tk.TclError:
                pass

    def run_async(
        self,
        action: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[ApiError], None] | None = None,
    ) -> None:
        def worker() -> None:
            try:
                result = action()
            except ApiError as exc:
                self._results.put((None, on_error, None, exc))
                return
            except Exception as exc:  # noqa: BLE001 兜底，避免线程静默退出
                self._results.put((None, on_error, None, ApiError(0, str(exc))))
                return
            self._results.put((on_success, None, result, None))

        threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    parser = argparse.ArgumentParser(description="课堂情绪检查器桌面客户端")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="后端地址")
    args = parser.parse_args()
    app = DesktopApp(args.base_url)
    app.mainloop()


if __name__ == "__main__":
    main()
