"""特征之间的距离 = 对称 KL 散度；歌曲之间的距离 = EMD（推土机距离）。

原文用 rpy2 调 R 的 lpSolve 解运输问题，这里用 scipy.optimize.linprog（HiGHS）
解同一个线性规划，省掉 R 依赖。
"""
import numpy as np
from scipy.optimize import linprog


def kl_div(mu1, S1, mu2, S2, inv_S2=None):
    """正态分布 N1 -> N2 的 KL 散度：

        0.5 * [ tr(S2^-1 S1) + (mu2-mu1)^T S2^-1 (mu2-mu1) - d + ln(det S2 / det S1) ]

    KL 本身不对称，所以下面再对称化。
    """
    inv_S2 = np.linalg.inv(S2) if inv_S2 is None else inv_S2
    d = len(mu1)
    t1 = float(np.trace(inv_S2 @ S1))
    delta = mu2 - mu1
    t2 = float(delta @ inv_S2 @ delta)
    logdet = float(np.linalg.slogdet(S2)[1] - np.linalg.slogdet(S1)[1])
    return 0.5 * (t1 + t2 - d + logdet)


def sym_kl(mu1, S1, mu2, S2, inv_S1=None, inv_S2=None):
    """对称 KL 散度：两个方向取平均，保证 d(P,Q) == d(Q,P)。"""
    a = kl_div(mu1, S1, mu2, S2, inv_S2)
    b = kl_div(mu2, S2, mu1, S1, inv_S1)
    return 0.5 * (a + b)


def _quad(inv_cov, mu_p, mu_q):
    """返回 (len(mu_q), len(mu_p))：每对 (p,q) 的 (mu_p-mu_q)^T inv_cov_p (mu_p-mu_q)。"""
    # c 是高斯类编号，a/b 是矩阵的两个维度，q 是另一首歌的类编号。
    # 把这四个下标分开写，避免把矩阵维度误当成同一个下标而只算到对角项。
    g = np.einsum("cab,cb->ca", inv_cov, mu_p)          # inv_cov_c @ mu_p_c
    q_p = np.einsum("ca,ca->c", mu_p, g)               # mu_p^T inv_cov_c mu_p
    term = np.einsum("cab,qa,qb->qc", inv_cov, mu_q, mu_q)
    cross = -2.0 * np.einsum("qa,ca->qc", mu_q, g)
    return term + cross + q_p[None, :]


def kl_matrix(s1, s2):
    """KL(类i -> 类j) 的 k1 x k2 矩阵，一次把所有类对算完（向量化版 kl_div）。"""
    d = s1.mu.shape[1]
    tr = np.einsum("jab,iba->ij", s2.inv_cov, s1.cov)     # tr(S2_j^-1 S1_i)
    quad = _quad(s2.inv_cov, s2.mu, s1.mu)                # (i, j)
    logdet = s2.logdet[None, :] - s1.logdet[:, None]
    return 0.5 * (tr + quad - d + logdet)


def cost_matrix(s1, s2):
    """两个指纹之间 k1 x k2 的代价矩阵：C[i,j] = symKL(类i, 类j)。

    和 sym_kl 完全对应：两个方向取平均，所以 C 天然满足 C12 == C21^T。
    """
    return 0.5 * (kl_matrix(s1, s2) + kl_matrix(s2, s1).T)


def emd(s1, s2, C=None):
    """两个指纹之间的 EMD。

    运输问题：把 s1 的 16 个类当成 16 个"发货点"（货量=权重），
    s2 的 16 个类当成"收货点"，把货从 i 搬到 j 的单位运费是 C[i,j]，
    求总运费最小的搬法。所有权重先归一化到总和 1，所以解出来的最小值就是 EMD。
    """
    if C is None:
        C = cost_matrix(s1, s2)
    # 理论上的对称 KL 非负；浮点运算可能产生约 -1e-12 的舍入误差。
    C = np.maximum(np.asarray(C, dtype=np.float64), 0.0)
    w1 = s1.w / s1.w.sum()
    w2 = s2.w / s2.w.sum()
    k1, k2 = C.shape
    n = k1 * k2

    # 等式约束：每行出货量 = w1[i]，每列收货量 = w2[j]
    # 两边总量都是 1，所以最后一条列约束是冗余的，去掉避免矩阵奇异
    A_eq = np.zeros((k1 + k2 - 1, n))
    for i in range(k1):
        A_eq[i, i * k2:(i + 1) * k2] = 1.0
    for j in range(k2 - 1):
        A_eq[k1 + j, j::k2] = 1.0
    b_eq = np.concatenate([w1, w2[:-1]])

    res = linprog(C.reshape(-1), A_eq=A_eq, b_eq=b_eq,
                  bounds=(0, None), method="highs")
    if not res.success:
        raise RuntimeError("EMD 线性规划求解失败: %s" % res.message)
    return float(res.fun)
