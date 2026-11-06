# 表情符号课堂情绪检查器系统 API 接口文档

## 1 接口约定
### 1.1 请求与认证

| 项目 | 约定 |
| --- | --- |
| 本机地址 | `http://127.0.0.1:8000`，局域网访问时替换主机地址 |
| 数据格式 | UTF-8，JSON 请求体使用 `Content-Type: application/json` |
| 用户认证 | `Authorization: Bearer <JWT>`；有效期默认 60 分钟，由部署配置控制 |
| AI 认证 | `X-AI-Service-Key: <服务密钥>`；独立于用户 JWT，并校验设备及课堂授权 |
| 分页 | `page` 从 1 开始；`page_size` 默认 20，范围 1—100，默认值及上限由配置控制 |
| 时间 | 使用 ISO 8601，调用方统一携带 `Z` 或 `+08:00` 等时区；库内 UTC，界面和导出使用北京时间 |
| 时间校验 | 创建、修改课堂必须带时区；查询时间及 AI 观测时间省略时区时，后端按 UTC 解释 |
| 区间 | 课堂和时间查询使用左闭右开区间 `[开始, 结束)` |
| 事件编号 | `event_id` 为 8—36 位字符串；建议使用 UUID 十六进制字符串，接口不强制 UUID 格式 |

学生只能查询本人手动记录；教师只能查询所授课程；管理员查询全部业务数据。CSV 导出仅向管理员开放。修改密码或账号启停后，原 JWT 立即失效。

### 1.2 响应、分页与错误

普通业务响应统一包含 `code`、`message`、`data`、`request_id`。`code=0` 表示成功，`request_id` 同时出现在响应头 `X-Request-Id`，用于关联日志。

```json
{"code":0,"message":"ok","data":{"items":[],"page":1,"page_size":20,"total":0},"request_id":"req-example"}
```

分页接口的 `data` 固定为 `{items, page, page_size, total}`，其余接口按各节说明返回对象或数组。失败时 `data=null`，`errors` 提供校验详情或为空。

```json
{"code":40900,"message":"课堂已开始，名单不可修改","data":null,"errors":null,"request_id":"req-example"}
```

| HTTP 状态 | 业务码 | 含义 |
| --- | --- | --- |
| 200 / 201 | 0 | 查询、操作成功 / 创建成功 |
| 401 | 40100 / 40101 | 凭据缺失、失效 / 用户名或密码错误 |
| 403 | 40300 | 角色无权限、设备未授权或登录账号停用 |
| 404 | 40400 | 对象不存在或不在可见范围；学生访问统计接口也返回此状态 |
| 409 | 40900 | 重名、课堂冻结、时间片或事件内容冲突、受保护账号停用 |
| 422 | 42200 | 字段、枚举、时间、邀请码或业务参数不合法 |
| 429 | 42900 | 登录或提交请求过于频繁 |
| 500 / 503 | 50000 / 50300 | 服务内部错误 / 服务暂不可用 |

### 1.3 枚举与返回对象

| 枚举 | 取值 |
| --- | --- |
| 角色 `role` | `STUDENT`、`TEACHER`、`ADMIN` |
| 用户状态 `status` | `ACTIVE`、`DISABLED` |
| 课堂状态 `status` | `PENDING`、`ONGOING`、`ENDED`、`CANCELLED` |
| 来源 `source` | `MANUAL`、`AI` |
| 表情 `emotion` | `HAPPY`、`NEUTRAL`、`SAD`、`ANGRY`、`SURPRISED`、`FEARFUL`、`DISGUST` |

以下对象名称用于后文返回类型说明；接口不返回密码哈希、服务密钥或令牌版本。

| 对象 | 字段 |
| --- | --- |
| 用户 `User` | `id, username, role, email, status, created_at`；`email` 可为空 |
| 课程 `Course` | `id, name, teacher_id, teacher_name, session_count, created_at` |
| 课堂 `Session` | `id, course_id, course_name, teacher_id, teacher_name, class_name, room, start_at, end_at, cancelled, ai_threshold, status, member_count, manual_count, ai_count` |
| 名单 `Members` | `session_id, member_count, items`；每个成员含 `user_id, username, arranged_at` |
| 记录 `Record` | `id, event_id, session_id, course_name, class_name, user_id, username, emotion, source, confidence, device_id, observed_at, received_at`；AI 用户字段为空，手动置信度及设备为空 |
| 审计 `Audit` | `id, actor_id, action, target_type, target_id, result, detail, created_at`；操作者、目标和详情可为空 |
| 分布 `Distribution` | 数组，每项为 `{emotion, count, ratio}`，`ratio` 为 0—1 的占比 |
| 趋势 `Trend` | 数组，每项为 `{bucket, manual, ai}`；按时间跨度选择 1、5、15、30 或 60 分钟粒度，空时间段补 0，跨天标签带日期 |

## 2 认证与用户管理

### 2.1 认证接口

| 方法与路径 | 权限 | 请求体 | 成功返回 `data` |
| --- | --- | --- | --- |
| `POST /auth/register` | 公开，按角色校验邀请码 | 注册字段见下表 | 201，`User` |
| `POST /auth/login` | 公开 | 必填 `username, password` | `{access_token, token_type, expires_at, user}`，`user` 为 `User` |
| `PUT /auth/password` | 已登录 | 必填 `old_password, new_password` | `{detail}`，提示重新登录 |

| 注册字段 | 必填 | 规则 |
| --- | --- | --- |
| `username` | 是 | 3—32 位，字母开头，仅字母、数字、下划线，且唯一 |
| `password` | 是 | 8—64 位，至少包含字母和数字 |
| `email` | 否 | 最多 120 位，填写时验证邮箱格式 |
| `role` | 否 | 省略或 `STUDENT` 为学生；`TEACHER`、`ADMIN` 须提供对应邀请码 |
| `invite_code` | 条件必填 | 最多 64 位；教师、管理员分别校验部署配置中的邀请码 |

注册重名返回 409，邀请码错误或入口关闭、弱密码返回 422。登录密码错误返回 401，密码正确但账号停用返回 403；已签发令牌遇账号停用时返回 401。修改密码须验证原密码，新密码遵守注册密码规则且不得与原密码相同。

```json
{"username":"student01","password":"Abc12345","email":"student01@example.com"}
```

### 2.2 用户与审计接口

| 方法与路径 | 权限 | 参数或请求体 | 成功返回 `data` |
| --- | --- | --- | --- |
| `GET /users/me` | 已登录 | 无 | 当前 `User` |
| `GET /admin/users` | 管理员 | 分页；可选 `role, status, keyword`，关键字最多 40 位 | 分页 `User` |
| `POST /admin/users` | 管理员 | 必填 `username, password, role`，可选 `email`；规则同注册，角色仅 `STUDENT/TEACHER` | 201，`User` |
| `PATCH /admin/users/{user_id}/status` | 管理员 | `{"status":"ACTIVE"}` 或 `{"status":"DISABLED"}` | 更新后的 `User` |
| `GET /admin/teachers` | 管理员 | 无 | 教师 `User` 数组 |
| `GET /admin/audit-logs` | 管理员 | 分页；可选 `action`，最多 60 位 | 分页 `Audit` |

## 3 课程、课堂与名单

### 3.1 查询与维护接口

| 方法与路径 | 权限 | 输入 | 成功返回 `data` |
| --- | --- | --- | --- |
| `GET /courses` | 已登录，按角色范围 | 无 | `Course` 数组 |
| `POST /admin/courses` | 管理员 | `name`：1—80 位；`teacher_id`：正整数，均必填 | 201，`Course` |
| `GET /sessions` | 已登录，按角色范围 | 分页；可选 `course_id, class_name, status` | 分页 `Session` |
| `GET /sessions/{session_id}` | 已登录，按课堂范围 | 路径课堂 ID | `Session` |
| `POST /admin/sessions` | 管理员 | 课堂创建字段见下表 | 201，`Session` |
| `PATCH /admin/sessions/{session_id}` | 管理员 | 可更新字段见下表 | 更新后的 `Session` |
| `GET /admin/sessions/{session_id}/members` | 教师或管理员，按课堂范围 | 路径课堂 ID | `Members` |
| `PUT /admin/sessions/{session_id}/members` | 管理员 | `{"user_ids":[4,5,6]}`，最多 500 项，可为空数组 | 保存后的 `Members` |
| `GET /admin/classes` | 教师或管理员，按课程范围 | 无 | `[{class_name, session_count}]` |

| 课堂字段 | 创建 | 修改 | 规则 |
| --- | --- | --- | --- |
| `course_id` | 必填 | 不接受修改 | 正整数，课程须存在 |
| `class_name` | 必填 | 可选 | 1—60 位，统一全角半角和空白 |
| `room` | 可选 | 可选 | 最多 60 位 |
| `start_at, end_at` | 必填 | 可选 | 必须带时区，结束晚于开始 |
| `ai_threshold` | 默认 0.6 | 可选 | 0—1 |
| `cancelled` | 创建时为 false | 可选 | 布尔值，取消后状态为 `CANCELLED` |

```json
{"course_id":1,"class_name":"计科2101","room":"A301","start_at":"2026-11-05T08:00:00+08:00","end_at":"2026-11-05T09:40:00+08:00","ai_threshold":0.6}
```

课程只能指定启用教师，同一教师下课程名重复返回 409。课堂状态按服务器时间计算，取消优先；仅未开始课堂可修改或保存名单，其他状态返回 409。名单整体替换并去重，非学生、停用或不存在用户返回 422；课堂不可见返回 404。

## 4 表情提交与历史查询

### 4.1 提交表情

`POST /emoji`，仅学生。请求必填 `event_id`、正整数 `session_id` 和七类之一的 `emotion`；学生身份、来源和时间由后端确定。

```json
{"event_id":"a3f1c2d4e5b6470891a2b3c4d5e6f708","session_id":6,"emotion":"HAPPY"}
```

```json
{"code":0,"message":"提交成功","data":{"record_id":275,"observed_at":"2026-11-05T00:32:03Z","duplicate":false},"request_id":"req-example"}
```

不在名单返回 403；课堂未开始、结束、取消或时间片被占用返回 409。默认同一学生、课堂每 30 秒时间片最多一条，配置为 0 时不限制。同事件同内容重试返回原记录及 `duplicate=true`，内容冲突返回 409；已成功事件在课堂结束后重试仍可确认原结果。

### 4.2 历史与参与学生

| 方法与路径 | 权限与范围 | 输入 | 成功返回 `data` |
| --- | --- | --- | --- |
| `GET /emoji/history` | 学生本人手动记录；教师所授课程；管理员全部 | 分页及下表筛选参数 | 分页 `Record` |
| `GET /sessions/{session_id}/students` | 教师或管理员，按课堂范围 | 路径课堂 ID | `[{user_id, username, record_count}]`，仅有手动记录的学生 |

历史、统计和导出共用以下筛选参数，均可省略；ID 为正整数，`class_name` 最多 60 位。

| 参数 | 含义 |
| --- | --- |
| `course_id, session_id, class_name` | 课程、课堂、班级 |
| `from, to` | 观测时间起止，左闭右开；客户端应带时区 |
| `source` | `MANUAL` 或 `AI` |
| `emotion` | 七类表情之一 |
| `user_id` | 学生；教师查历史时使用此项须同时指定 `session_id`，否则 422 |

学生传入他人 `user_id` 或 `source=AI` 时，后端仍固定查询本人 MANUAL 记录。历史按观测时间倒序返回。

## 5 看板、统计与 CSV

| 方法与路径 | 权限 | 输入 | 成功返回 |
| --- | --- | --- | --- |
| `GET /dashboard/realtime` | 教师或管理员 | 必填正整数 `session_id` | 看板对象，见下表 |
| `GET /statistics` | 教师或管理员 | 第 4.2 节筛选参数 | 统计对象，见下文 |
| `GET /admin/emoji/export` | 仅管理员 | 第 4.2 节筛选参数 | CSV 文件流 |

教师查询自动限定所授课程，访问其他教师课堂看板返回 404；教师调用导出接口返回 403。学生访问规范统计路径返回 404。

### 5.1 看板数据

| `data` 字段 | 内容 |
| --- | --- |
| `session_id, course_name, class_name, status` | 课堂基础信息及状态 |
| `manual` | `{total, participants, member_count, coverage, distribution}` |
| `ai` | `{total, threshold, last_observed_at, distribution}`，无 AI 记录时样本时间为空 |
| `trend` | `Trend`，同一序列分别包含手动和 AI 次数 |
| `last_update_at` | 本次服务端汇总时间 |

参与人数仅按手动学生去重；覆盖率为参与人数除以名单人数，名单为空时返回 `null`，界面显示“不适用”。看板分布按各自来源计算占比，AI 次数是观察次数，不代表独立学生人数。

### 5.2 多维统计数据

返回 `{total, manual_total, ai_total, participants, distribution, by_source, trend, filters}`。`distribution` 按当前筛选记录总数计算占比；只需某一来源时传入 `source`。`participants` 只统计手动学生，`source=AI` 时为 0；跨课堂不计算覆盖率。

`filters` 回显 `course_id, session_id, class_name, from, to, source`；`emotion` 和 `user_id` 虽参与筛选，但不在此回显对象中。

### 5.3 CSV 文件
字段为记录 ID、课程、班级、课堂开始时间、学生账号、表情、来源、置信度、观测时间、接收时间、设备；AI 学生账号单元格为空。

```text
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename="emoji_records_20261105_090000.csv"
X-Export-Rows: 2
```

## 6 AI 服务接口

### 6.1 获取课堂配置

`GET /ai/context`，携带服务密钥；必填正整数 `session_id` 和 1—60 位 `device_id`。返回：

`{session_id, course_name, class_name, start_at, end_at, status, ai_threshold, sample_interval_seconds, max_faces_per_frame, emotions}`。

采样间隔默认 3 秒，每帧人脸上限默认 5。设备或课堂未授权返回 403，密钥缺失、错误或服务端未配置密钥返回 401，课堂不存在返回 404。

### 6.2 批量上传结果

`POST /ai/emoji-results`，携带服务密钥。顶层与事件字段均为必填。

| 字段 | 类型与规则 |
| --- | --- |
| `device_id` | 1—60 位字符串，须匹配设备授权 |
| `session_id` | 正整数，授权课堂 ID |
| `model_version` | 1—60 位字符串 |
| `results` | 1—100 个事件 |
| `results[].event_id` | 8—36 位唯一事件字符串 |
| `results[].observed_at` | ISO 8601 观测时间 |
| `results[].emotion` | 七类表情之一 |
| `results[].confidence` | 0—1 的数值，等于课堂阈值可接收 |

```json
{"device_id":"demo-device-01","session_id":6,"model_version":"opencv-zoo-fer-2022july","results":[{"event_id":"f782d88b0fda403296349326b6ccfb5f","observed_at":"2026-11-05T00:32:03Z","emotion":"NEUTRAL","confidence":0.7366}]}
```

以下为该单事件被接收时的响应示例；示例时间应在课堂进行中且满足事件时效条件。

```json
{"code":0,"message":"批次已处理","data":{"accepted":1,"duplicates":0,"rejected":0,"details":[{"event_id":"f782d88b0fda403296349326b6ccfb5f","status":"ACCEPTED","reason":null,"record_id":277}]},"request_id":"req-example"}
```

逐事件 `status` 为 `ACCEPTED`、`DUPLICATE` 或 `REJECTED`。同事件内容一致的重试返回原记录；事件已成功后即使课堂结束，也先确认重复结果。新增事件的拒绝原因如下。

| `reason` | 含义 |
| --- | --- |
| `SESSION_NOT_ONGOING` | 课堂不在进行中 |
| `OUT_OF_SESSION_WINDOW` | 观测时间不在课堂区间 |
| `OBSERVED_TOO_OLD` | 超过允许回溯时间，默认 60 秒 |
| `OBSERVED_IN_FUTURE` | 超过允许未来偏差，默认 5 秒 |
| `BELOW_THRESHOLD` | 置信度低于课堂阈值 |
| `EVENT_ID_CONFLICT` | 事件编号被不同内容占用或并发冲突 |

缺字段、非法枚举、置信度越界或批量超限返回请求级 422，整批不写入；业务拒绝则 HTTP 200，在 `details` 中逐条说明。AI 记录由服务端固定来源 AI、用户为空，不上传图像或人脸特征。

## 7 实时通知与服务入口

### 7.1 WebSocket

连接地址：`ws://127.0.0.1:8000/ws/dashboard?session_id=6&token=<JWT>`。教师仅订阅所授课堂，学生仅订阅本人名单内课堂，管理员可订阅全部课堂。认证或课堂权限检查失败时统一关闭，关闭码为 `4401`。

```json
{"type":"connected","session_id":6}
```

```json
{"type":"emoji.created","session_id":6,"source":"MANUAL","record_id":275}
```

AI 新增记录通知使用 `{"type":"emoji.created","session_id":6,"source":"AI","accepted":1}`。消息只表示数据变化，收到后调用看板 REST 接口重新查询；页面可见时每 3 秒轮询作为断线补充，离开页面停止。

### 7.2 健康检查与在线文档

- `GET /health` 无需认证，不加业务前缀，直接返回 `{status, env, database}`，不套业务响应。
- `/docs` 提供 Swagger 调试，`/redoc` 提供只读文档，`/openapi.json` 返回机器可读接口定义；仓库保存的契约为 [openapi.json](openapi.json)。

### 7.3 已提供的兼容路径

以下路径同样添加 `/api/v1` 前缀，与规范接口共用业务逻辑和权限规则。

| 兼容路径 | 对应规范路径 |
| --- | --- |
| `GET /admin/dashboard/realtime` | `GET /dashboard/realtime` |
| `GET /admin/statistics`、`GET /emoji/statistics` | `GET /statistics` |
| `POST /admin/sessions/{session_id}/schedule` | `PUT /admin/sessions/{session_id}/members` |
