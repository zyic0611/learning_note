"""向量量化：k-means 聚类。

原文用 scipy.cluster.vq.kmeans，这里自己写一遍，方便讲原理、也能控制随机初始化。
把 3000 个 20 维 MFCC 帧压成 16 个"代表帧"（聚类中心），这就是压缩的第一步。
"""
import numpy as np


def kmeanspp_init(X, k, rng):
    """k-means++ 初始化：让初始中心尽量互相远离。"""
    n = len(X)
    centers = [X[rng.integers(n)]]
    d2 = ((X - centers[0]) ** 2).sum(axis=1)
    for _ in range(1, k):
        total = d2.sum()
        p = np.full(n, 1.0 / n) if total <= 0 else d2 / total
        centers.append(X[rng.choice(n, p=p)])
        d2 = np.minimum(d2, ((X - centers[-1]) ** 2).sum(axis=1))
    return np.array(centers)


def _lloyd(X, centers, max_iter, tol):
    """Lloyd 迭代：反复「分配 -> 更新中心」直到收敛。"""
    k = len(centers)
    labels = np.zeros(len(X), dtype=int)
    x2 = np.einsum("nd,nd->n", X, X)[:, None]
    for _ in range(max_iter):
        # ||x-c||² = ||x||² - 2x·c + ||c||²，避免构造 (帧数,k,维度) 三维临时数组。
        c2 = np.einsum("kd,kd->k", centers, centers)[None, :]
        d2 = np.maximum(x2 - 2.0 * X @ centers.T + c2, 0.0)
        new_labels = d2.argmin(axis=1)
        new_centers = centers.copy()
        for c in range(k):
            member = X[new_labels == c]
            if len(member) == 0:
                # 空簇：把它挪到离自己中心最远的那个点上，避免死簇
                new_centers[c] = X[d2.min(axis=1).argmax()]
            else:
                new_centers[c] = member.mean(axis=0)
        shift = ((new_centers - centers) ** 2).sum()
        centers, labels = new_centers, new_labels
        if shift <= tol:
            break
    inertia = ((X - centers[labels]) ** 2).sum()
    return labels, centers, inertia


def kmeans(X, k=16, n_init=5, max_iter=100, tol=1e-4, seed=0):
    """跑 n_init 次取失真最小的一组。返回 (labels, centers, inertia)。"""
    X = np.asarray(X, dtype=np.float64)
    best = None
    for i in range(n_init):
        rng = np.random.default_rng(seed + i)
        centers = kmeanspp_init(X, k, rng)
        labels, centers, inertia = _lloyd(X, centers, max_iter, tol)
        if best is None or inertia < best[2]:
            best = (labels, centers, inertia)
    return best
