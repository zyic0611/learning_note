# 基于多语料库与说话人隔离评估的语音情感识别研究

> 本文档是可直接填充的研究报告框架。所有数值必须来自实验产物，不得凭空填写。默认读取 `../api/artifacts/metrics.json`；各模型原始报告见 `../api/artifacts/metrics-cnn.json` 与 `../api/artifacts/metrics-svm.json`。提交前将“待填”替换为产物中的值，并注明产物版本或哈希。

## 摘要

本文研究六分类语音情感识别问题，类别依次为 neutral、happy、sad、angry、fear、disgust。研究使用 RAVDESS 与 CREMA-D，采用以说话人为分组单位的交叉验证，比较卷积神经网络与基于手工声学特征的 SVM。主要评价指标为未加权平均召回率（UAR），并报告 Accuracy、混淆矩阵、分类别召回率与分语料结果。最终模型的 **UAR、Accuracy 与其不确定性待从 `metrics.json` 填入**。实验强调避免同一说话者跨训练/测试集合造成的信息泄漏，并讨论跨语料分布偏移与部署限制。

**关键词：** 语音情感识别；说话人隔离；UAR；卷积神经网络；支持向量机；跨语料评估

## 1. 引言

### 1.1 研究背景

- 语音情感识别的应用背景与研究意义。
- 声学情绪表达的主观性、语境依赖和跨域差异。
- 类别不平衡下仅报告 Accuracy 的不足。

### 1.2 研究问题

1. 在说话人隔离的设置下，CNN 与 SVM 的六分类性能如何？
2. 模型对不同情绪类别、不同语料库的表现是否一致？
3. 能量 VAD、固定 3 秒窗口及数据预处理如何影响推理结果？

### 1.3 主要贡献

- 统一 RAVDESS 与 CREMA-D 的六类标签映射。
- 建立可复现的说话人隔离交叉验证流程。
- 在同一数据划分下比较 Mel-CNN 与手工特征 SVM。
- 提供文件与流式推理系统，并明确模型就绪、静音与 ASR 不可用状态。

## 2. 相关工作

### 2.1 语音情感识别方法

综述传统低层描述符、统计函数、SVM，以及时频表示与 CNN 的典型路线。补充正式引用：[待填文献 1–N]。

### 2.2 数据集与跨语料问题

介绍 RAVDESS、CREMA-D 的采集方式、演员/说话人、标签获得方式及许可。引用数据集原始论文，而非仅引用下载页面：[待填]。

### 2.3 评价协议

说明随机按样本切分会引入说话人泄漏；对比 speaker-independent、cross-corpus 等协议及其适用范围。

## 3. 数据与预处理

### 3.1 数据来源

| 语料库 | 原始样本数 | 纳入样本数 | 说话人数 | 标注方式 | 许可证/引用 |
|---|---:|---:|---:|---|---|
| RAVDESS | 待查原始论文 | 待从 metadata 统计 | 待统计 | 演绎标签 | 待填 |
| CREMA-D | 待查原始论文 | 待从 metadata 统计 | 待统计 | 多评审投票 | 待填 |

数据来源脚本：`../api/ser/data/download.py`。样本清单及说话人字段由 `../data/cache/features-v1.metadata.json` 自动生成，应以该文件为统计依据。

### 3.2 标签映射

固定类别顺序：

```text
neutral, happy, sad, angry, fear, disgust
```

- RAVDESS 的 calm 与 surprised 被排除，避免仅由单一语料提供类别而形成语料识别捷径。
- CREMA-D 的标签清洗及歧义样本规则：参见 `../api/ser/data/labels.py`；报告中补充实际阈值 `[待填]`。
- 给出每类、每语料的样本数表 `[由 metadata 自动统计后填入]`。

### 3.3 音频预处理

统一为单声道、采样率 \(f_s=16\,000\ \text{Hz}\)。每个输入裁剪或补零至 3 秒。预加重：

\[
y[t] = x[t] - \alpha x[t-1], \qquad \alpha=0.97.
\]

短时傅里叶变换使用 `N_FFT=512`、窗长 400 点、帧移 160 点；Mel 频带数为 64，频率范围为 20–8000 Hz。对每个 Mel 频带执行均值—方差归一化：

\[
\hat{M}_{k,t}=\frac{\log(M_{k,t}+\epsilon)-\mu_k}{\max(\sigma_k,10^{-5})}.
\]

最终 CNN 输入张量形状为 \(64\times 300\)。以上常量应自动对照 `../api/ser/config.py`，如配置变更需同步本节。

### 3.4 手工声学特征

SVM 特征包括 F0、清浊度、RMS、对数能量、过零率、13 维 MFCC 及其一阶差分、谱质心、谱通量、85% 谱滚降点；对各帧序列计算 mean、std、min、max，形成 136 维向量。实现参见 `../api/ser/features/handcrafted.py`。

## 4. 方法

### 4.1 CNN 模型

- 结构：从 `../api/ser/models/cnn.py` 自动整理层级、通道数、池化和参数量 `[待填]`。
- 损失：带类别权重的交叉熵。训练样本数为 \(N\)，第 \(c\) 类样本数为 \(n_c\)，有效类别数为 \(C'\) 时：

\[
w_c=\frac{N}{C'n_c},\qquad
\mathcal{L}_{CE}=-\sum_c w_c y_c\log p_c.
\]

- 数据增强：SpecAugment 与 Mixup。Mixup 形式为：

\[
\tilde{x}=\lambda x_i+(1-\lambda)x_j,\quad
\tilde{y}=\lambda y_i+(1-\lambda)y_j,
\quad \lambda\sim\operatorname{Beta}(0.2,0.2).
\]

- 优化器、学习率、权重衰减、batch size、early stopping：从训练命令和 `metrics-cnn.json` 填入 `[待填]`。

### 4.2 SVM 基线

描述特征标准化、核函数、类别权重、概率校准及超参数。实现参见 `../api/ser/models/svm.py`；将实际参数表填入 `[待填]`。

### 4.3 数据划分

使用 \(K=5\) 折说话人隔离交叉验证。设说话人集合为 \(S\)，同一说话人的全部样本只能属于同一分区：

\[
S_{train}^{(k)}\cap S_{val}^{(k)}=
othing,\quad
S_{train}^{(k)}\cap S_{test}^{(k)}=
othing,\quad
S_{val}^{(k)}\cap S_{test}^{(k)}=
othing.
\]

说明训练/验证/测试折的构造、随机种子 `1337`，并从 `metrics-*.json.per_fold[*].sizes` 填入每折规模。

### 4.4 模型选择

每折模型以验证集 UAR 选择；服务产物为验证 UAR 最高的折模型。明确指出：该单折模型并非用全部训练数据重训，最终部署性能不能直接等同于完整 OOF 指标。若后续增加全量重训，应在此更新协议。

## 5. 评价指标

设共有 \(C=6\) 类，混淆矩阵为 \(M\)，其中 \(M_{ij}\) 表示真实类别 \(i\) 被预测为 \(j\) 的样本数。

### 5.1 Accuracy

\[
\mathrm{Accuracy}=\frac{\sum_{c=1}^{C}M_{cc}}{\sum_{i=1}^{C}\sum_{j=1}^{C}M_{ij}}.
\]

### 5.2 分类别召回率与 UAR

\[
R_c=\frac{M_{cc}}{\sum_{j=1}^{C}M_{cj}},\qquad
\mathrm{UAR}=\frac{1}{C}\sum_{c=1}^{C}R_c.
\]

UAR 对每个类别等权，更适合类别不平衡的 SER。若某折缺少某类，应说明实现中的缺失类处理方式。

### 5.3 Macro-F1（如产物提供）

\[
P_c=\frac{M_{cc}}{\sum_i M_{ic}},\quad
F1_c=\frac{2P_cR_c}{P_c+R_c},\quad
\mathrm{MacroF1}=\frac{1}{C}\sum_c F1_c.
\]

当前核心产物若未包含 Macro-F1，应标记“不适用”，不得从 Accuracy 或 UAR 推算。

### 5.4 不确定性与显著性

当前产物提供点估计与分折结果。正式论文建议增加按说话人 bootstrap 的 95% 置信区间，并对两模型使用配对检验。报告随机种子、bootstrap 次数和检验方法 `[待实现/待填]`。

## 6. 实验设置

| 项目 | 配置 |
|---|---|
| 运行环境 | Docker / Python 3.11 / CPU `[补充硬件]` |
| 随机种子 | 1337 |
| 折数 | 5 |
| 主指标 | UAR |
| CNN epochs / patience | 40 / 7（若命令覆盖则填实际值） |
| Batch size | 32（若命令覆盖则填实际值） |
| SVM 参数 | 从源码/运行配置填入 |
| 产物路径 | `../api/artifacts/metrics.json` |
| 产物哈希 | `[运行 sha256 后填入]` |

复现实验命令：

```bash
./scripts/download_data.sh
./scripts/train.sh precompute
./scripts/train.sh svm --folds all
./scripts/train.sh cnn --folds all --epochs 40 --patience 7
./scripts/export.sh cnn
```

## 7. 结果

> 下列所有表格必须以产物为唯一数据源。若字段不存在，写“未计算”，不要补造数值。

### 7.1 总体性能

| 模型 | OOF 样本数 | Accuracy | UAR | Macro-F1 | 产物来源 |
|---|---:|---:|---:|---:|---|
| SVM | 待填 | 待填 | 待填 | 未计算/待填 | `metrics-svm.json.out_of_fold` |
| CNN | 待填 | 待填 | 待填 | 未计算/待填 | `metrics-cnn.json.out_of_fold` |

描述观察，不只报告“谁更高”：差值、折间波动、类别不平衡、实际意义及不确定性均需讨论。

### 7.2 分折结果

| Fold | 模型 | 训练/验证/测试规模 | Validation UAR | Test UAR | Test Accuracy |
|---:|---|---|---:|---:|---:|
| 0–4 | SVM/CNN | 从 `per_fold.sizes` 填入 | 待填 | 待填 | 待填 |

建议图：每折 UAR 点图/箱线图。图表必须从 JSON 生成并保留生成脚本或 notebook 引用 `[待补]`。

### 7.3 分类别表现

| 类别 | SVM Recall | CNN Recall | 支持数 |
|---|---:|---:|---:|
| neutral | 待填 | 待填 | 待填 |
| happy | 待填 | 待填 | 待填 |
| sad | 待填 | 待填 | 待填 |
| angry | 待填 | 待填 | 待填 |
| fear | 待填 | 待填 | 待填 |
| disgust | 待填 | 待填 | 待填 |

数据路径：`out_of_fold.per_class_recall` 与 `out_of_fold.support`。

### 7.4 混淆矩阵

插入由 `out_of_fold.confusion_matrix` 生成的图 `[待生成]`。横轴为预测类别，纵轴为真实类别，标签顺序必须与配置一致。除原始计数外，建议展示按真实类别归一化版本。

### 7.5 分语料结果

| 模型 | 语料库 | 样本数 | Accuracy | UAR |
|---|---|---:|---:|---:|
| SVM/CNN | RAVDESS | 待填 | 待填 | 待填 |
| SVM/CNN | CREMA-D | 待填 | 待填 | 待填 |

数据路径：`out_of_fold.per_corpus`。讨论不同语料的表演方式、录音条件和标签机制差异。

## 8. 消融与误差分析

### 8.1 建议消融

- 不使用 SpecAugment。
- 不使用 Mixup。
- 不使用类别权重。
- 只使用单一语料训练/测试。
- 1 秒、3 秒、5 秒窗口对比。
- 能量 VAD 开启/关闭，仅作为服务层误触发分析，不与分类准确率混为一谈。

当前如未运行这些实验，明确写“待实验”，不要据机制推断数值收益。

### 8.2 误差案例

按混淆对（例如 happy→neutral）抽样。对每个案例记录：语料、说话人、时长、信噪情况、人工标签、模型概率、转写、声学现象。避免公开可识别个人信息或受限音频。

## 9. 系统实现与部署

- API：FastAPI，文件接口与 WebSocket 流式接口。
- 流式策略：16 kHz 单声道 PCM16，滚动 3 秒窗口，约 1 秒更新。
- VAD：帧能量与自适应噪声阈值；静音不调用 SER。
- ASR：faster-whisper small、CPU int8、惰性加载；不可用时不影响 SER。
- 并发：CPU 密集型 SER/ASR 使用同一互斥锁并在线程池执行，避免阻塞事件循环和 CPU 争抢。
- 部署：Nginx 容器内 80 端口，同源代理到 API；宿主机仅开放 3000。

延迟、吞吐、内存与镜像大小均需实测后填入：`[待基准测试]`。

## 10. 讨论

### 10.1 有效性威胁

- **内部有效性：** 划分实现、标签映射、模型选择偏差、随机性。
- **外部有效性：** 语料以表演情绪为主，语言与设备覆盖有限。
- **构念有效性：** 离散情绪标签并不等同于真实心理状态。
- **统计结论有效性：** 样本和说话人数量有限；当前缺少置信区间和显著性检验。

### 10.2 公平性、隐私与伦理

分析可能的语言、性别、口音、年龄等群体偏差；未经授权不得留存声音或转写；系统不得用于高风险自动决策。若报告分群指标，应保证样本量足够并避免反向识别。

## 11. 结论与未来工作

总结应仅依据第 7 节真实结果。未来工作可包括：真实自然语音验证、跨语料留一测试、预训练语音编码器、置信度校准、说话人 bootstrap、端到端延迟评估与隐私保护。

## 参考文献

1. RAVDESS 原始论文与数据集条款 `[待填标准格式]`。
2. CREMA-D 原始论文与数据集条款 `[待填标准格式]`。
3. 语音情感识别综述 `[待填]`。
4. SpecAugment、Mixup、UAR 等方法来源 `[待填]`。
5. 使用的软件包/模型按版本与许可证引用 `[待填]`。

## 附录 A：产物字段对照

| 报告内容 | JSON 路径 |
|---|---|
| 模型类型 | `model_type` |
| 随机种子 | `seed` |
| 折数/运行折 | `n_folds`, `folds_run` |
| 每折结果 | `per_fold[*]` |
| 每折规模 | `per_fold[*].sizes` |
| 每折验证/测试指标 | `per_fold[*].val`, `per_fold[*].test` |
| OOF 总指标 | `out_of_fold` |
| 混淆矩阵 | `out_of_fold.confusion_matrix` |
| 分类别召回/支持数 | `out_of_fold.per_class_recall`, `out_of_fold.support` |
| 分语料指标 | `out_of_fold.per_corpus` |
| 服务选中模型 | `best_artifact`, `selection` |

## 附录 B：提交前核对

- [ ] 所有数值可追溯到已归档 JSON，且模型/数据版本一致。
- [ ] 标签顺序为 neutral、happy、sad、angry、fear、disgust。
- [ ] 明确按说话人隔离，不将样本随机切分描述成 speaker-independent。
- [ ] 不把最高验证折模型的表现误称为完整 OOF 性能。
- [ ] 图表轴、归一化方式和样本数标注完整。
- [ ] 未计算的指标明确写“未计算”，无推测数字。
- [ ] 数据集、代码、依赖与预训练模型引用和许可完整。
- [ ] 伦理、隐私、公平性和使用边界已说明。
