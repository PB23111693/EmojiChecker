# AI 推理进程

从摄像头或回放视频采样，检测人脸、分类表情、按课堂阈值过滤，并把匿名结果批量上传到后端。进程独立于 Web 服务运行，只持有 AI 服务密钥，不接触用户令牌。

## 1 运行前提

- Python 3.10 以上，安装 `requirements.txt`
- 已下载模型：`python scripts/download_models.py`
- 后端已启动，`.env` 中的 `AI_SERVICE_KEY`、`AI_DEVICE_ID` 与本进程配置一致
- 课堂处于进行中，且已保存名单（名单不参与 AI 记录，但演示需要）

## 2 快速开始

```powershell
cd ai-worker
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe scripts\download_models.py
Copy-Item config.example.yaml config.yaml
# 编辑 config.yaml 的 session_id，service_key 可用环境变量 AI_SERVICE_KEY 提供
..\.venv\Scripts\python.exe run.py --config config.yaml
```

常用参数：

| 参数 | 说明 |
| --- | --- |
| `--session-id` | 覆盖配置文件中的课堂 ID |
| `--camera` | 摄像头序号，默认 0 |
| `--video path` | 使用回放视频；界面与日志标注“回放输入” |
| `--threshold 0.6` | 覆盖课堂阈值，仅用于联调 |
| `--interval 3` | 采样间隔，默认 3 秒 |
| `--once` | 只采样一帧，用于联调 |
| `--no-display` | 无窗口运行 |
| `--no-wait` | 课堂未开始时立即退出 |

无摄像头的开发机可用回放文件联调：

```powershell
..\.venv\Scripts\python.exe run.py --video samples\demo.mp4 --once --no-display
```

回放结果不得在演示中冒充现场采集。

## 3 处理流程

```text
摄像头/视频 → 取帧（间隔 3 秒）→ YuNet 检测 → 五点对齐 112×112
→ 表情 ONNX 推理 → softmax 取最大类 → 阈值与尺寸过滤
→ 匿名事件入队 → 批量上传 → 后端二次校验入库
```

- 采集：`ai_worker/capture.py`，摄像头与回放共用接口。
- 检测：`ai_worker/detect.py`，YuNet 动态输入模型。
- 分类：`ai_worker/classify.py`，读取 7 维 logits 并 softmax。
- 过滤：`ai_worker/filter.py`，低于阈值、尺寸过小、超过每帧上限均丢弃并计数。
- 上传：`ai_worker/uploader.py`，批量 100 条，退避 1/2/4/8 秒，单事件 30 秒上限。
- 主循环：`ai_worker/runner.py`，每 30 秒刷新课堂状态，结束后停止采集。

## 4 与后端的契约

- 认证：请求头 `X-AI-Service-Key`，取值来自环境变量 `AI_SERVICE_KEY`，不与用户令牌混用。
- 取配置：`GET /api/v1/ai/context?session_id=&device_id=`，返回课堂时间窗、`ai_threshold`、七类枚举与采样参数。
- 上报：`POST /api/v1/ai/emoji-results`，批量不超过 100 条。

服务端规则：

- 整批字段非法返回 422，且零写入；本进程整批丢弃并记录错误。
- 通过校验后返回 200，逐事件给出 `ACCEPTED`、`DUPLICATE` 或 `REJECTED` 及原因。
- 低于阈值 `BELOW_THRESHOLD`，课堂非进行中 `SESSION_NOT_ONGOING`，事件编号冲突 `EVENT_ID_CONFLICT`。逐事件拒绝不重试。
- 网络失败或 5xx 才重试；401/403 立即停止并提示配置错误。

## 5 模型与参数

| 项目 | 取值 |
| --- | --- |
| 人脸检测 | YuNet `face_detection_yunet_2026may.onnx`，动态输入 |
| 表情分类 | MobileFaceNet `facial_expression_recognition_mobilefacenet_2022july.onnx` |
| 输入 | 640×480 采集，五点对齐后 112×112 RGB |
| 采样间隔 | 3 秒，处理超时降为 5 秒 |
| 阈值 | 课堂配置，默认 0.60，服务端按同值二次校验 |
| 每帧最多人脸 | 5 |
| 最小人脸边长 | 48 像素 |

模型输出为 logits，代码执行 softmax；得分未经校准，不等于判断正确的概率。模型来源、许可与 SHA256 见 `models/README.md`。

## 6 隐私约束

- 视频帧只在内存中使用，检测后释放，不写盘、不缓存特征向量。
- 上传内容只有事件 ID、时间、表情类别、置信度、设备与模型版本，不含人脸图像或身份信息。
- 日志不记录可识别个人的信息；回放输入在日志与界面中明确标注。
- 摄像头画面默认只在本机预览，不对外提供视频流。

## 7 测试

```powershell
..\.venv\Scripts\python.exe -m pytest tests -q
```

测试覆盖阈值过滤、类别映射、上传重试与 422 整批丢弃。模型文件缺失时，涉及推理的用例自动跳过。
