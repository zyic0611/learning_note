"""MFCC 提取（纯 numpy 实现，对应原文里的 x2x|frame|mfcc 那一段）。

参数与原文一致：
  采样率 16 kHz / 帧长 400 样本(25ms) / 帧移 160 样本(10ms) / Mel 通道 40
  MFCC 取 19 维 + 对数能量 = 20 维
所以 30 秒音频 = 3000 帧，得到一个 3000x20 的矩阵，和原文的 3000 行 20 维一致。
"""
import numpy as np

FS = 16000
FRAME_LEN = 400
FRAME_HOP = 160
N_FFT = 512
N_MELS = 40
N_CEP = 19          # 倒谱系数个数：c0..c18
DIM = N_CEP + 1     # + 单独的对数能量 = 20


def hz2mel(f):
    return 2595.0 * np.log10(1.0 + f / 700.0)


def mel2hz(m):
    return 700.0 * (10.0 ** (m / 2595.0) - 1.0)


def mel_filterbank(n_mels=N_MELS, n_fft=N_FFT, fs=FS, fmin=0.0, fmax=None):
    """三角 Mel 滤波器组，形状 (n_mels, n_fft//2+1)。"""
    fmax = fs / 2.0 if fmax is None else fmax
    edges = mel2hz(np.linspace(hz2mel(fmin), hz2mel(fmax), n_mels + 2))
    bins = np.floor((n_fft + 1) * edges / fs).astype(int)
    n_bins = n_fft // 2 + 1
    bins = np.clip(bins, 0, n_bins - 1)
    fb = np.zeros((n_mels, n_bins))
    for i in range(n_mels):
        l, c, r = bins[i], bins[i + 1], bins[i + 2]
        if c <= l:
            c = l + 1
        if r <= c:
            r = c + 1
        for k in range(l, min(c, n_bins)):
            fb[i, k] = (k - l) / float(c - l)
        for k in range(c, min(r, n_bins)):
            fb[i, k] = (r - k) / float(r - c)
    return fb


def dct_matrix(n_out, n_in):
    """DCT-II 变换矩阵（正交归一）。"""
    n = np.arange(n_in)
    k = np.arange(n_out)[:, None]
    m = np.cos(np.pi * (2 * n + 1) * k / (2.0 * n_in)) * np.sqrt(2.0 / n_in)
    m[0] *= 1.0 / np.sqrt(2.0)
    return m


def frame_signal(x, frame_len=FRAME_LEN, hop=FRAME_HOP):
    """分帧，返回 (num_frames, frame_len)。

    每隔 hop 取一帧，末尾不足 frame_len 的部分补零。因此 30 秒、16 kHz、
    帧移 160 样本时恰好得到 3000 帧，和项目材料中的计数一致。
    """
    n = max(1, int(np.ceil(len(x) / float(hop))))
    needed = (n - 1) * hop + frame_len
    if len(x) < needed:
        x = np.pad(x, (0, needed - len(x)))
    idx = np.arange(frame_len)[None, :] + hop * np.arange(n)[:, None]
    return x[idx]


def extract_mfcc(x, fs=FS, fb=None, dct=None, cmn=False):
    """波形 -> (num_frames, 20) 的 MFCC 矩阵。

    cmn=True 时做倒谱均值归一化（减去每维均值，去掉声道/音量带来的整体偏移）。
    """
    if fs != FS:
        raise ValueError("MFCC 参数固定为 %d Hz，请先重采样" % FS)
    if fb is None:
        fb = mel_filterbank(fs=fs)
    if dct is None:
        # 这里采用语音/音乐处理中常见的 19 个倒谱系数 c0..c18；
        # 再附加原始帧的对数能量，共 20 维。c0 概括 Mel 频谱整体水平，
        # 对数能量来自加窗后时域信号，二者相关但定义不同。
        dct = dct_matrix(N_CEP, N_MELS)

    frames = frame_signal(x)
    frames = frames * np.hamming(FRAME_LEN)[None, :]

    spec = np.fft.rfft(frames, n=N_FFT, axis=1)
    power = (np.abs(spec) ** 2)

    mel_energy = power @ fb.T                      # (T, N_MELS)
    log_mel = np.log(mel_energy + 1e-10)

    cep = log_mel @ dct.T                          # (T, N_CEP) = c1..c19
    energy = np.log((frames ** 2).sum(axis=1) + 1e-10)[:, None]

    mfcc = np.hstack([cep, energy]).astype(np.float64)
    if cmn:
        mfcc = mfcc - mfcc.mean(axis=0, keepdims=True)
    return mfcc
