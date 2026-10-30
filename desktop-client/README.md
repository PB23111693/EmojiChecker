# 桌面客户端（C/S 通道）

使用 Python 标准库 tkinter 与 urllib 实现的桌面客户端，与 Web 端共用同一套 REST 接口。指导书要求 C/S 与 B/S 混合架构，本客户端承担 C/S 通道中的客户端角色，AI 进程不承担业务操作。

## 1 功能范围

| 流程 | 说明 |
| --- | --- |
| 登录 | 用户名与密码登录，令牌只保存在内存，退出即清除 |
| 选择课堂 | 列出本人被安排的课堂，显示课程、班级、教室、时间与状态 |
| 提交表情 | 仅在“进行中”课堂启用，提交七类表情之一，显示成功或失败原因 |
| 查看历史 | 分页查看本人手动记录，含时间、课程、班级、表情与来源 |
| 修改密码 | 校验原密码，成功后要求重新登录 |

不包含管理端的建课、排人、导出功能；这些操作在 Web 管理端完成。

## 2 运行

```powershell
cd desktop-client
..\.venv\Scripts\python.exe client.py
```

默认连接 `http://127.0.0.1:8000`，可指定后端地址：

```powershell
..\.venv\Scripts\python.exe client.py --base-url http://192.168.1.10:8000
```

演示账号见仓库根目录 README。客户端不需要安装第三方依赖。

## 3 结构说明

`client.py` 分为三个部分：

- `ApiClient`：REST 访问与统一错误解析，对应 MVVM 中的 Repository。
- `LoginFrame`、`MainFrame`：视图与交互，课堂、反馈、历史、账号四个页签。
- `DesktopApp`：窗口装配与后台线程结果队列。

所有网络请求在后台线程执行，结果放入 `queue.Queue`，由主线程轮询后更新界面，避免 tkinter 跨线程操作控件。令牌不写入磁盘，关闭程序即失效。

## 4 与其他端的关系

```text
桌面客户端 ── REST/JSON ──┐
Web 客户端  ── REST/JSON ──┤──> 后端 Controller → Service → Repository → 数据库
AI 进程     ── REST/JSON ──┘
```

三端使用同一 API 契约与统一响应结构。桌面客户端的提交请求与 Web 端完全相同，服务端按登录身份确定学生 ID，客户端不能指定他人身份或记录来源。
