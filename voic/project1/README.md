# 项目 1：相似歌曲检索系统

这是一个**基于音频内容**的相似歌曲检索系统。输入不是歌名、歌手或用户行为，而是歌曲波形本身。

系统按导师材料中的基础路线实现：

```text
音频文件
  → 转成 16 kHz 单声道，截取中间 30 秒
  → 提取 20 维 MFCC（3000 帧）
  → k-means 聚成 16 类
  → 每类用「权重 + 均值 + 协方差」描述
  → 类与类之间计算对称 KL 散度
  → 歌与歌之间计算 EMD（推土机距离）
  → 线性扫描并按距离从小到大排序
```

项目不过度使用高级模型，没有神经网络或预训练模型，重点是能理解、能讲清楚、能现场演示。

## 已完成内容

- 纯 NumPy 实现 MFCC 和 k-means，代码可直接学习
- 使用 SciPy 线性规划求 EMD，不再依赖 R、rpy2 和 lpSolve
- 支持 WAV、MP3、FLAC、M4A、AAC、OGG、WMA
- 自带 48 首无版权问题的合成演示歌曲，分为 6 个音色家族
- Web 页面支持从曲库选择歌曲，也支持上传自己的音频
- 每条结果都能直接试听中间 30 秒
- 提供全库评估：Top-1、Precision@5、Recall@5、mAP
- 18 项数学与格式自检
- Docker 打包，Intel Mac 和 Apple Silicon Mac 均可运行

## Mac 上最快运行方式

### 1. 安装 Docker Desktop

下载并启动 [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)。

- Apple Silicon（M1/M2/M3/M4/M5）和 Intel Mac 都支持
- 等菜单栏里的 Docker 图标显示运行完成后再执行下面命令
- 第一次构建镜像需要联网下载 Python、SciPy 和 ffmpeg

### 2. 启动项目

在终端进入本项目目录：

```bash
cd project1
bash docker.sh start
```

构建完成后打开：

<http://localhost:8088>

推荐第一次演示选择：**“霓虹脉冲 — NEON-9 [合成器]”**。

### 3. 停止项目

```bash
bash docker.sh stop
```

## Docker 常用命令

```bash
# 构建并启动 Web 演示
bash docker.sh start

# 查看容器日志
bash docker.sh logs

# 运行 18 项数学自检
bash docker.sh test

# 命令行检索演示库中的一首歌
bash docker.sh search 合成器-01

# data/songs 中更换歌曲后，重新提取全部特征并评估
bash docker.sh rebuild-index

# 重新计算评估指标
bash docker.sh evaluate

# 从头生成 48 首演示歌曲、建库并评估
bash docker.sh demo-reset

# 停止 Web 服务
bash docker.sh stop
```

> `docker.sh` 同时兼容新版 `docker compose` 和旧版 `docker-compose`。Dockerfile 没有固定 CPU 架构，Docker Desktop 会自动选择 amd64 或 arm64 基础镜像。

## 网页演示方法

### 使用自带歌曲

1. 打开 <http://localhost:8088>
2. 下拉选择歌曲
3. 点击“检索相似歌曲”
4. 观察 EMD 距离和绿色同家族行
5. 点击音频播放器，试听查询歌曲与检索结果

### 上传自己的歌曲

1. 点击文件选择框，选择 MP3/WAV 等音频
2. 点击“上传并检索”
3. 系统在容器中完成解码、MFCC、聚类和 EMD 排序
4. 上传文件只用于当前检索，不会写入曲库

单个上传文件限制为 100 MB。系统只分析中间 30 秒。

## 使用自己的歌曲建立曲库

1. 停止网页：

   ```bash
   bash docker.sh stop
   ```

2. 将音频放进 `data/songs/`。文件名必须唯一。
3. 如果不需要原演示歌曲，可先把它们移动到项目目录之外。
4. 重新建库：

   ```bash
   bash docker.sh rebuild-index
   ```

5. 再启动：

   ```bash
   bash docker.sh start
   ```

如果自己的歌曲没有 `family` 标签，检索仍可正常运行；只是评估脚本无法判断“同家族是否命中”。元数据格式见 `data/meta.json`：

```json
{
  "songs": {
    "文件名（不含扩展名）": {
      "title": "显示标题",
      "artist": "艺术家",
      "family": "用于评估的类别"
    }
  }
}
```

## 当前演示数据和真实评估

演示库共 48 首，每个家族 8 首：

- 钢琴
- 电钢琴
- 木吉他
- 弦乐
- 长笛
- 合成器

每首歌轮流作为查询，排除歌曲本身；同家族的其他 7 首作为相关结果。最终评估：

| 指标 | 结果 |
|---|---:|
| Top-1 Accuracy | **79.2%** |
| Precision@5 | **67.5%** |
| Recall@5 | **48.2%** |
| mAP | **71.8%** |

评估页面：<http://localhost:8088/evaluation>

这些指标由 `scripts/evaluate.py` 对 1,128 对歌曲距离实际计算得到，不是手写数字。合成器、弦乐和长笛区分效果最好；钢琴、电钢琴和木吉他更容易互相混淆，这符合“只依赖音色特征”的预期。

## 项目结构

```text
project1/
├── app.py                       # Web 服务与页面
├── Dockerfile                  # 多架构容器镜像
├── compose.yaml                # 数据目录挂载、端口映射
├── docker.sh                   # Mac/Linux 一键命令
├── requirements.txt
├── mirtool/
│   ├── audio.py                # 音频读取、重采样、截取
│   ├── mfcc.py                 # MFCC 提取
│   ├── vq.py                   # k-means 向量量化
│   ├── signature.py            # 高斯指纹
│   ├── distance.py             # KL 和 EMD
│   ├── pipeline.py             # 建库流水线
│   ├── search.py               # 线性检索
│   └── report.py               # 单次检索 HTML 报告
├── scripts/
│   ├── make_demo_library.py    # 生成无版权演示歌曲
│   ├── build_index.py          # 批量建库
│   └── evaluate.py             # 全库评估
├── tests/test_basic.py         # 18 项自检
├── data/
│   ├── songs/                  # 原始歌曲
│   ├── clips/                  # 中间 30 秒试听片段
│   ├── sig/                    # 每首歌的指纹
│   └── meta.json               # 标题、艺术家、评估标签
├── out/
│   ├── evaluation.html         # 离线评估页
│   ├── evaluation.json         # 指标和逐首排名
│   └── distances.npz           # 全库距离矩阵缓存
└── docs/
    ├── 原理讲解.md
    ├── 演示与答辩.md
    └── 项目报告.md
```

## 不使用 Docker 的开发方式

最终交付推荐 Docker。只有需要调试代码时才使用本机 Python：

```bash
python3 -m pip install -r requirements.txt
python3 tests/test_basic.py
python3 app.py
```

读取 MP3 等压缩格式还需系统 ffmpeg；Docker 镜像已经包含它。

## 局限和可扩展方向

1. MFCC 主要描述频谱包络和音色，不直接描述旋律。
2. 当前把帧看成无序集合，基本忽略时间顺序和节奏结构。
3. 中间 30 秒不一定正好是副歌。
4. 线性扫描适合几百首；百万规模需要向量索引、候选召回或并行计算。
5. 可加入 chroma（和声/旋律）、tempogram（节奏）后做加权融合，但本项目刻意保持基础和可解释。

详细原理见 [docs/原理讲解.md](docs/原理讲解.md)，现场流程和问答见 [docs/演示与答辩.md](docs/演示与答辩.md)。
