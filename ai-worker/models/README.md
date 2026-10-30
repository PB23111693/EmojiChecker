# 模型文件

模型文件体积较大，不提交仓库。执行 `python scripts/download_models.py` 下载并校验。

| 文件 | 用途 | 大小 | SHA256 | 许可 |
| --- | --- | --- | --- | --- |
| `face_detection_yunet_2026may.onnx` | YuNet 人脸检测，动态输入 | 约 225 KB | `ebafce4e3c118d6554634be5c27ab333b4c047a9a8c3faf1d7cf93101c22f0f0` | MIT |
| `facial_expression_recognition_mobilefacenet_2022july.onnx` | MobileFaceNet 表情分类，7 类 | 约 4.6 MB | `4f61307602fc089ce20488a31d4e4614e3c9753a7d6c41578c854858b183e1a9` | Apache-2.0 |

来源：OpenCV Zoo。
- https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet
- https://github.com/opencv/opencv_zoo/tree/main/models/facial_expression_recognition

## 已验证事实

2026 年 10 月 29 日在 OpenCV 5.0.0、ONNX Runtime 1.20.1、NumPy 2.3.2 上实际验证：

1. 选择 `2026may` 版 YuNet，是因为 OpenCV 5.x 的 ONNX Runtime 引擎要求动态输入维度，`2023mar` 版为固定输入，可能无法在不同分辨率下推理。
2. 表情模型输入为 `data`，形状 `(1, 3, 112, 112)`；输出为 `label`，形状 `(1, 7)`。
3. 输出是 logits，不是概率：随机输入下存在负值，且各维之和不为 1。因此代码执行 softmax 后取最大类得分作为置信度。
4. 类别顺序取自官方封装：`angry, disgust, fearful, happy, neutral, sad, surprised`，与字母序不同，映射表写在 `ai_worker/classify.py`。
5. 预处理为五点对齐到 112×112、RGB、除以 255、减 0.5 除 0.5。在公开测试人像上得到 neutral 0.81，流程可用。

置信度是模型 softmax 得分，未经本项目校准，不等于判断正确的概率。该结论写入结题报告的局限性分析。
