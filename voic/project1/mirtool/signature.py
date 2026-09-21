"""特征指纹（signature）：把一首歌的 3000x20 MFCC 压成 16 个高斯分布。

每首歌的指纹 = 16 行，每行 1 + 20 + 400 = 421 个数：
    权重 w（落进这一类的帧数）、均值向量 mu（20 维）、协方差矩阵 Sigma（20x20，拉平）
和原文的 .sig 文件格式完全一致，方便对照。
"""
import os

import numpy as np

from .vq import kmeans

DIM = 20
K = 16
RIDGE = 1e-3   # 协方差正则化系数，见下面注释


def build_signature(mfcc, k=K, ridge=RIDGE, seed=0, n_init=5):
    """MFCC 矩阵 -> Signature。"""
    mfcc = np.asarray(mfcc, dtype=np.float64)
    d = mfcc.shape[1]
    labels, centers, inertia = kmeans(mfcc, k=k, n_init=n_init, seed=seed)

    # 全曲方差，用来给"帧数太少导致协方差不可用"的情况兜底
    fallback = float(np.var(mfcc, axis=0).mean()) + 1e-8

    weights = np.zeros(k)
    means = np.zeros((k, d))
    covs = np.zeros((k, d, d))
    for c in range(k):
        frames = mfcc[labels == c]
        weights[c] = len(frames)
        if len(frames) == 0:
            means[c] = centers[c]
            covs[c] = np.eye(d) * fallback
            continue
        means[c] = frames.mean(axis=0)
        if len(frames) < 2:
            covs[c] = np.eye(d) * fallback
        else:
            # 样本协方差（除以 N-1），和项目材料中的 np.cov(frames.T) 一致
            covs[c] = np.cov(frames.T)
        # 正则化：给对角线加一点点扰动，保证协方差可逆。
        # 帧数少 / 维度高时协方差接近奇异，求逆会爆炸，KL 散度就算不出有意义的数。
        covs[c] += np.eye(d) * (ridge * float(np.trace(covs[c])) / d + 1e-8)

    return Signature(weights, means, covs)


class Signature:
    """一首歌的指纹，附带预计算好的协方差逆矩阵（算距离时反复要用）。"""

    def __init__(self, weights, means, covs):
        self.w = np.asarray(weights, dtype=np.float64)
        self.mu = np.asarray(means, dtype=np.float64)
        self.cov = np.asarray(covs, dtype=np.float64)
        self.inv_cov = np.linalg.inv(self.cov)
        # ln(det(Sigma))，KL 散度里要用；预先算好，算距离时就不用反复求行列式
        self.logdet = np.linalg.slogdet(self.cov)[1]

    @property
    def k(self):
        return len(self.w)

    def to_matrix(self):
        """拼成 (k, 421) 的矩阵，用于存文件。"""
        k, d = self.mu.shape
        rows = np.hstack([self.w[:, None], self.mu, self.cov.reshape(k, d * d)])
        return rows

    def save(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        mat = self.to_matrix()
        with open(path, "w") as f:
            for row in mat:
                f.write(" ".join("%.6g" % v for v in row) + "\n")

    @classmethod
    def load(cls, path):
        rows = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append([float(v) for v in line.split()])
        mat = np.array(rows)
        k = mat.shape[0]
        d = int(round(np.sqrt(mat.shape[1] - 1)))
        return cls(mat[:, 0], mat[:, 1:1 + d], mat[:, 1 + d:].reshape(k, d, d))
