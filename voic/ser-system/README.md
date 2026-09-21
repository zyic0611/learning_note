# 语音情感识别系统

一个面向研究演示的 CPU 语音情感识别（SER）系统。标签及顺序固定为：`neutral, happy, sad, angry, fear, disgust`。系统包含说话人隔离训练、文件分析、实时 PCM 流分析、可选语音转写和可视化前端。

## 架构

```text
浏览器 :3000
  └─ Nginx（静态站点，容器内 :80）
       └─ /api/* 反向代理
            └─ FastAPI :8000（仅 Compose 内网）
                 ├─ EmotionRecognizer / CPU
                 ├─ 能量 VAD
                 ├─ faster-whisper small / int8 / CPU（可选）
                 └─ /app/artifacts ← ./api/artifacts

训练容器（training profile）
  ├─ ./data/raw   → /data/raw
  ├─ ./data/cache → /data/cache
  └─ ./api/artifacts → /app/artifacts
```

运行时只向宿主机开放 `http://localhost:3000`。API 与 WebSocket 走 Nginx 同源代理；不单独暴露 API 端口。

## macOS 启动

要求 Docker Desktop（含 Docker Compose v2）；支持 Apple Silicon，不固定容器平台。所有命令只在 Docker 内安装依赖和运行服务，不要在宿主机执行 `pip install`、`npm install` 或启动开发服务器。

```bash
cd /mnt/data/yichengzhu_workspace/voic/ser-system
./scripts/up.sh
open http://localhost:3000
```

如果还没有 `api/artifacts/active/best-*.pt|joblib`，这是正常的：API 仍会启动，`GET /api/health` 返回 `model_ready: false`，预测接口返回 503，不会生成伪预测。完成训练和导出后重启：

```bash
./scripts/export.sh cnn       # 或 svm
./scripts/down.sh
./scripts/up.sh
```

检查部署链路：

```bash
./scripts/smoke_test.sh
./scripts/down.sh
```

## ASR 模型首次运行

默认镜像构建**不下载** faster-whisper 模型，避免网络波动导致构建失败。第一次提交需要转写的音频时，服务会从 Hugging Face 下载 `small` 模型至 Docker volume `asr_models`；首次响应可能较慢。下载失败只会使 `transcript.available=false`，不影响 SER。API 基础镜像默认为公开的 `python:3.11-slim-bookworm`；仅在私有镜像代理环境中可用 `PYTHON_IMAGE=镜像地址 ./scripts/up.sh` 覆盖。

可选配置：

```bash
# 构建时预下载（需要稳定外网，镜像会显著变大）
DOWNLOAD_ASR_MODEL=true ./scripts/up.sh

# 仅使用已缓存或挂载的模型，禁止运行时下载
ASR_LOCAL_ONLY=true ./scripts/up.sh

# 完全禁用转写
ASR_ENABLED=false ./scripts/up.sh
```

也可在 Compose 中挂载模型目录并设置 `ASR_MODEL_PATH`。默认计算配置为 `small + CPU + int8`。模型加载是惰性的，因此 `/api/health` 中 `asr_ready` 在首次转写前可为 `false`，同时 `asr_status=not_loaded`。

## 数据、训练与导出

数据集下载自 RAVDESS 与 CREMA-D 的公开镜像。下载量较大；请确认磁盘空间和数据集许可。

```bash
# 1. 下载数据到 data/raw
./scripts/download_data.sh

# 2. 生成 Mel 与手工特征缓存
./scripts/train.sh precompute

# 3. 快速验证训练链路
./scripts/train.sh smoke svm
./scripts/train.sh smoke cnn

# 4. 正式训练（说话人隔离交叉验证）
./scripts/train.sh svm --folds all
./scripts/train.sh cnn --folds all --epochs 40 --patience 7

# 5. 选择模型作为服务产物，并生成 api/artifacts/metrics.json
./scripts/export.sh cnn
```

`train.sh` 会把附加参数直接传给对应 Python CLI。`export.sh` 将 `best-<model>` 原子复制到 `api/artifacts/active/`，并将该模型的评估报告复制为 `api/artifacts/metrics.json`；`GET /api/metrics` 直接读取此文件。

## 演示流程

1. 打开首页，确认模型状态为可用。
2. 在“音频文件分析”上传 WAV、MP3、M4A 或 WebM（最多 25 MB、最长 5 分钟）。
3. 查看主导情绪、六类概率、转写、3 秒时间线、波形与 Mel 热图。
4. 在“实时识别”授权麦克风。浏览器发送 16 kHz、单声道、little-endian PCM16；服务端保留滚动 3 秒窗口，约每 1 秒更新。
5. 静音由能量 VAD 拦截，返回 `label: null` 与全零概率，不调用模型。
6. 在“模型评估”查看 `api/artifacts/metrics.json` 对应的实验结果。

## API 契约

- `GET /api/health`：进程、SER readiness 和 ASR 状态。
- `GET /api/models`：标签顺序、模型路径、采样率及窗口。
- `GET /api/metrics`：读取 `api/artifacts/metrics.json` 并适配为前端稳定对象，字段为 `labels, uar, macroF1, accuracy, comparison, confusionMatrix, folds, dataset, sampleCount, model, source`；未生成时为 404。训练产物目前没有 Macro-F1 时返回 `null`，不伪造数值。
- `POST /api/predict?language=zh&transcribe=true`：multipart 字段名 `file`，支持 WAV/MP3/M4A/WebM。
- `WS /api/ws/stream`：连接后首先发送配置 JSON，再发送 PCM16 二进制块。

WebSocket 首条消息：

```json
{"type":"config","sample_rate":16000,"channels":1,"format":"pcm_s16le","language":"zh","transcribe":false}
```

文件预测的稳定顶层字段为 `labels`、`audio`、`prediction`、`transcript`、`timeline`、`waveform`、`mel`。`prediction` 为：

```json
{
  "label": "happy",
  "confidence": 0.82,
  "probabilities": {
    "neutral": 0.05,
    "happy": 0.82,
    "sad": 0.03,
    "angry": 0.06,
    "fear": 0.02,
    "disgust": 0.02
  }
}
```

前端集成必须遵守这些假设：标签严格按上述六类及顺序；静音时 `label` 可为 `null`；`transcript` 是对象而不是字符串；波形使用 `waveform.min/max` 包络；热图矩阵位于 `mel.values`；时间线情绪字段名为 `label`。WebSocket 收到 `ready` 后才应发送音频，服务端的 `prediction` 消息复用 `prediction`、`transcript`、`timeline` 结构。当前仓库前端若仍使用旧的扁平字段或 `surprise` 标签，需由其维护者按本节适配。

## 限制与排障

- 情绪标签是语料映射结果，不代表说话者真实心理状态，不应用于医疗、招聘、执法或其他高风险决策。
- 数据域、语言、麦克风、噪声和人群差异会造成分布漂移；报告指标不能直接代表生产效果。
- CPU 上 ASR 和 SER 共用单通道推理锁，优先保证稳定性而非高并发；长音频会较慢。
- 上传内容先经大小、扩展名和 MIME 检查，再由无 shell 的 ffmpeg 子进程解码；默认上限 25 MB / 300 秒。
- 查看日志：`docker compose logs -f api`；查看状态：`docker compose ps`。
- `model_ready=false`：先检查 `api/artifacts/active/` 中是否恰有一个 `best-*.pt` 或 `best-*.joblib`，再重启 API。
- ASR 下载失败：确认 Docker 可访问 Hugging Face，或预下载/挂载模型；也可设置 `ASR_ENABLED=false`。
- 麦克风只允许安全上下文。`http://localhost:3000` 和 `http://127.0.0.1:3000` 在现代浏览器中可用；不要用局域网 IP 的纯 HTTP。若必须跨设备访问，请配置 HTTPS，并检查浏览器站点权限、系统麦克风权限和占用情况。

## 许可与归属

代码许可应以仓库最终附带的 `LICENSE` 为准；在未提供许可证前，不默认授予再分发权。RAVDESS、CREMA-D、faster-whisper/CTranslate2、PyTorch、FastAPI、React、Nginx 等数据集、模型与依赖保留各自许可证和引用要求。发布模型、报告或演示前，应分别核对并注明数据集作者、论文、下载来源及使用条款。
