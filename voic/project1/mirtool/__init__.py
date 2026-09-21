"""相似歌曲检索（Music Information Retrieval）最小实现。

流程：音频 -> 中间 30 秒 -> MFCC(20 维/帧) -> k-means 向量量化(16 类)
      -> 每类的高斯(权重/均值/协方差) = 歌曲指纹
      -> 两首歌之间用 对称 KL 散度 算类间距离、用 EMD 算整首距离
      -> 线性扫描排序得到相似歌曲
"""
from .audio import load_audio, center_segment, write_wav, TARGET_FS
from .mfcc import extract_mfcc, DIM
from .vq import kmeans
from .signature import Signature, build_signature
from .distance import emd, sym_kl, kl_div, cost_matrix
from .pipeline import (signature_from_audio, build_library, load_signatures,
                       load_index_config)

__all__ = [
    "load_audio", "center_segment", "write_wav", "TARGET_FS",
    "extract_mfcc", "DIM", "kmeans",
    "Signature", "build_signature",
    "emd", "sym_kl", "kl_div", "cost_matrix",
    "signature_from_audio", "build_library", "load_signatures", "load_index_config",
]
