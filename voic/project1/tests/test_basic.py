#!/usr/bin/env python3
"""基础自检：确认每一步的数学是对的。直接 python3 tests/test_basic.py 跑。"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mirtool.distance import cost_matrix, emd, kl_div, sym_kl  # noqa: E402
from mirtool.audio import center_segment  # noqa: E402
from mirtool.mfcc import FRAME_HOP, FRAME_LEN, N_CEP, N_MELS, dct_matrix, extract_mfcc  # noqa: E402
from mirtool.signature import Signature, build_signature  # noqa: E402

OK, FAIL = [], []


def check(name, cond, extra=""):
    (OK if cond else FAIL).append(name)
    print("%s %s %s" % ("PASS" if cond else "FAIL", name, extra))


def ref_cost_matrix(s1, s2):
    """慢速参考实现：直接按定义双重循环算。"""
    C = np.zeros((s1.k, s2.k))
    for i in range(s1.k):
        for j in range(s2.k):
            C[i, j] = sym_kl(s1.mu[i], s1.cov[i], s2.mu[j], s2.cov[j])
    return C


def main():
    rng = np.random.default_rng(0)

    # 1. MFCC 帧数：30 秒 @16kHz，帧长 400、帧移 160 -> 应该是 3000 帧
    x = rng.standard_normal(16000 * 30) * 0.1
    mfcc = extract_mfcc(x)
    expect = 3000
    check("MFCC 帧数 = %d (30 秒)" % expect, mfcc.shape == (expect, 20), str(mfcc.shape))
    check("MFCC 20 维 (19 倒谱 + 对数能量)", mfcc.shape[1] == 20)
    used_dct = dct_matrix(N_CEP, N_MELS)
    check("MFCC 使用 c0..c18，共 19 个倒谱系数",
          used_dct.shape == (19, 40) and np.allclose(used_dct[0], used_dct[0, 0]))

    # 2. 分帧不重叠的边界：样本数刚好时帧数正确
    check("MFCC 有限值", np.isfinite(mfcc).all())
    whole = rng.standard_normal(16000 * 40)
    check("40 秒歌曲只截取中间总计 30 秒",
          len(center_segment(whole, 16000, 30.0)) == 16000 * 30)
    short = rng.standard_normal(16000 * 8)
    check("不足 30 秒时保留整首歌曲",
          len(center_segment(short, 16000, 30.0)) == len(short))

    # 3. KL 散度：自己到自己 = 0，且不对称性被对称化抹平
    mu1 = rng.standard_normal(20)
    A = rng.standard_normal((20, 20))
    S1 = A @ A.T + np.eye(20)
    mu2 = rng.standard_normal(20)
    B = rng.standard_normal((20, 20))
    S2 = B @ B.T + np.eye(20)
    check("symKL(x, x) == 0", abs(sym_kl(mu1, S1, mu1, S1)) < 1e-9)
    check("symKL 对称", abs(sym_kl(mu1, S1, mu2, S2) - sym_kl(mu2, S2, mu1, S1)) < 1e-9)
    check("KL 本身不对称", abs(kl_div(mu1, S1, mu2, S2) - kl_div(mu2, S2, mu1, S1)) > 1e-6)
    check("symKL >= 0", sym_kl(mu1, S1, mu2, S2) > 0)

    # 4. 向量化代价矩阵 == 慢速参考实现
    m1 = rng.standard_normal((200, 20))
    m2 = rng.standard_normal((200, 20)) + 0.5
    s1 = build_signature(m1, k=16, n_init=2, seed=1)
    s2 = build_signature(m2, k=16, n_init=2, seed=2)
    C_fast = cost_matrix(s1, s2)
    C_ref = ref_cost_matrix(s1, s2)
    check("代价矩阵与参考实现一致", np.allclose(C_fast, C_ref, rtol=1e-6, atol=1e-8),
          "max|diff|=%.2e" % np.abs(C_fast - C_ref).max())
    check("代价矩阵对称性 C12 == C21^T",
          np.allclose(cost_matrix(s1, s2), cost_matrix(s2, s1).T, rtol=1e-6, atol=1e-8))

    # 5. EMD：同指纹之间距离为 0；不同指纹之间 > 0
    check("EMD(x, x) == 0", abs(emd(s1, s1)) < 1e-8, "%.3e" % emd(s1, s1))
    check("EMD 对称", abs(emd(s1, s2) - emd(s2, s1)) < 1e-8)
    check("EMD(x, y) > 0", emd(s1, s2) > 0, "%.4f" % emd(s1, s2))

    # 6. EMD 对权重尺度不敏感（只和归一化后的分布有关）
    s1b = Signature(s1.w * 3.0, s1.mu, s1.cov)
    check("EMD 不受权重整体缩放影响", abs(emd(s1, s2) - emd(s1b, s2)) < 1e-8)

    # 7. 指纹存取往返一致
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "t.sig")
        s1.save(path)
        s1c = Signature.load(path)
        check("sig 文件往返一致",
              np.allclose(s1.mu, s1c.mu) and np.allclose(s1.cov, s1c.cov)
              and np.allclose(s1.w, s1c.w))
        with open(path) as f:
            ncol = len(f.readline().split())
        check("每行 421 个数 (1 权重 + 20 均值 + 400 协方差)", ncol == 421, "实际 %d" % ncol)

    print("\n%d 项通过, %d 项失败" % (len(OK), len(FAIL)))
    if FAIL:
        print("失败：", FAIL)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
