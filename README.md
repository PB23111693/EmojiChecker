# 表情符号课堂情绪检查器系统

软件工程实践课程大作业。系统支持学生在课堂中主动记录情绪，AI 进程从摄像头或回放视频采样并上报匿名表情分类结果，教师查看所授课堂的实时看板与统计，管理员完成排课、名单、数据查看与 CSV 导出。Web 端、桌面客户端与 AI 进程共用一套 REST 接口。

## 1 交付物与状态

| 部分 | 状态 | 说明 |
| --- | --- | --- |
| 后端 | 可运行 | FastAPI 分层结构，52 项自动化测试通过 |
| Web 前端 | 可运行 | Vue 3 + Element Plus + ECharts，构建产物由后端托管 |
| 桌面客户端 | 可运行 | tkinter，登录、选课、提交、历史、改密 |
| AI 推理进程 | 可运行 | YuNet + 表情 ONNX，回放输入已实测入库 |
| 数据库 | 可运行 | 默认 SQLite WAL；提供 MySQL 8 建表脚本，未完成 MySQL 全量回归 |
| 文档 | 已完成 | `docs/02` 至 `docs/11` |
| 演示视频 | 待录制 | 脚本见 `docs/10-演示视频脚本与提交清单.md` |

## 2 技术栈

| 层次 | 技术 |
| --- | --- |
| 后端 | Python 3.12、FastAPI 0.141、Pydantic 2.12、SQLAlchemy 2.0 |
| 数据库 | 默认 SQLite WAL，可选 MySQL 8 |
| 认证 | JWT HS256、Argon2id 密码哈希、令牌版本失效 |
| Web 前端 | Vue 3、Vite、Element Plus、ECharts |
| 桌面客户端 | Python 标准库 tkinter 与 urllib |
| AI | OpenCV 5.0、ONNX Runtime 1.20、YuNet、MobileFaceNet 表情模型 |
| 测试 | pytest、FastAPI TestClient |
| 部署 | 本机或局域网；可选 Docker Compose 与 Nginx |

## 3 快速开始

### 3.1 准备虚拟环境

Windows PowerShell，在仓库根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

若本机已安装 FastAPI 等依赖，可用 `python -m venv --system-site-packages .venv` 复用系统包，再补装 `argon2-cffi`、`PyJWT`、`opencv-python`、`onnxruntime`、`PyYAML`、`requests`。

### 3.2 配置

```powershell
Copy-Item .env.example .env
```

至少填写：

- `SECRET_KEY`：随机长字符串。留空时进程生成临时密钥，重启后所有令牌失效。
- `TEACHER_INVITE_CODE`：教师自助注册邀请码，留空关闭入口。
- `ADMIN_INVITE_CODE`：管理员自助注册邀请码，留空关闭入口；生产环境使用长随机值。
- `AI_SERVICE_KEY`：AI 进程服务密钥，必须与 `ai-worker/config.yaml` 或环境变量一致。

### 3.3 初始化数据并启动后端

```powershell
cd backend
..\.venv\Scripts\python.exe scripts\seed_demo.py --reset
$env:PYTHONUTF8=1
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

启动后访问：

- 系统页面 `http://127.0.0.1:8000`
- 接口文档 `http://127.0.0.1:8000/docs`
- 健康检查 `http://127.0.0.1:8000/health`

若前端尚未构建，先执行：

```powershell
cd frontend
npm install
npm run build
```

### 3.4 演示账号

| 角色 | 账号 | 密码 |
| --- | --- | --- |
| 管理员 | admin | Admin@2026 |
| 教师 | teacher_zhang | Emoji@2026 |
| 教师 | teacher_li | Emoji@2026 |
| 学生 | stu2021001 至 stu2021008 | Emoji@2026 |

演示密码仅用于本地初始化，正式部署必须修改。

### 3.5 启动桌面客户端

```powershell
cd desktop-client
..\.venv\Scripts\python.exe client.py
```

### 3.6 启动 AI 推理进程

```powershell
cd ai-worker
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe scripts\download_models.py
Copy-Item config.example.yaml config.yaml
# 修改 config.yaml 的 session_id，或使用 --session-id
..\.venv\Scripts\python.exe run.py --config config.yaml
```

无摄像头时可用回放视频联调：

```powershell
..\.venv\Scripts\python.exe run.py --video samples\demo.mp4 --once --no-display
```

## 4 运行测试

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest          # 52 项后端与接口测试

cd ..\ai-worker
..\.venv\Scripts\python.exe -m pytest          # 20 项 AI 单元测试

cd ..\desktop-client
..\.venv\Scripts\python.exe -m pytest          # 1 项轮询容错测试
```

测试覆盖认证与令牌失效、越权访问、课堂时间窗、名单去重、幂等与时间片、统计口径、CSV 公式注入、AI 阈值与时钟偏差、端到端排课与导出。每个测试函数的 docstring 首行标注对应验收用例编号。

## 5 目录说明

```text
backend/         后端应用，controller - service - repository 三层
frontend/        Web 客户端与管理端，controllers 与 composables 为修改版 MVC 的前端控制层
desktop-client/  桌面客户端，构成 C/S 通道
ai-worker/       AI 推理进程，独立部署，只上传匿名分类结果
db/              数据库脚本与说明
deploy/          Dockerfile 与 Nginx 配置
docs/            需求、设计、接口、测试、部署、手册、报告与提交清单
```

详细结构与分层职责见 `docs/01-项目结构说明.md`，架构与修改版 MVC 说明见 `docs/03-概要设计说明书.md`。

## 6 关键约定

- 统一响应结构为 `{code, message, data, request_id}`，错误同时返回对应 HTTP 状态码，`request_id` 与响应头 `X-Request-Id` 一致。
- 术语使用 `emoji` 表示表情符号，`emotion` 表示情绪类别；七类取值为 HAPPY、NEUTRAL、SAD、ANGRY、SURPRISED、FEARFUL、DISGUST。
- 课堂状态由服务器时间推导，区间为左闭右开 `[start_at, end_at)`，取消标记优先于时间状态。
- 手动记录与学生绑定，AI 记录固定匿名，两者在统计中分别计算，不合并为单一情绪得分。
- 原始人脸帧、视频与特征向量不落库、不入日志、不进仓库。
- 班级名在写入与查询时做全角半角与空白归一，但仍是课堂上的自由文本字段。

## 7 已知限制

- 开发与演示环境使用 SQLite；MySQL 8 只提供建表脚本与连接配置，未完成全量回归。
- Docker 配置已提供，构建环境未安装 Docker，未完成容器内实测。
- AI 在无摄像头环境用回放图片验证；真实摄像头链路需在演示机复核。
- AI 模型的表情得分未经本项目校准，不等于判断正确的概率。
- 限流为单进程内存实现，多进程部署需替换为共享存储。
- WebSocket 推送仅作变更信号，业务数据仍由 REST 拉取。
- 浏览器端到端自动化测试未在本机执行，前端以构建成功、接口契约核对与人工路径检查为准。

## 8 文档索引

| 文档 | 内容 |
| --- | --- |
| `docs/00-方案审核意见.md` | 方案审核结论、修正项与代码审查问题 |
| `docs/01-项目结构说明.md` | 目录、分层职责与当前进度 |
| `docs/02-需求规格说明书.md` | 角色、功能与非功能需求、用例 |
| `docs/03-概要设计说明书.md` | 架构、修改版 MVC、模块与流程 |
| `docs/04-数据库设计说明书.md` | ER 图、表结构、约束与统计口径 |
| `docs/05-接口文档.md` | 接口约定、路径、请求与响应 |
| `docs/06-测试报告.md` | 测试环境、用例结果、缺陷记录 |
| `docs/07-部署说明.md` | 本地、Docker、MySQL 与故障排查 |
| `docs/08-用户手册.md` | 三角色与 AI 操作步骤 |
| `docs/09-结题报告.md` | 完成情况、关键实现、实测与局限 |
| `docs/10-演示视频脚本与提交清单.md` | 录制流程与提交检查 |
| `docs/11-分工与贡献表.md` | 成员信息与贡献填写模板 |
| `docs/12-验收对照与人工核验手册.md` | 指导书逐项对照、M01 至 M20 人工核验步骤 |
