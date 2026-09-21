"""Deterministic polyphase audio resampling."""

from math import gcd

import numpy as np
from scipy.signal import resample_poly


def resample_audio(waveform: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    """Resample a mono waveform and return contiguous float32 samples."""
    waveform = np.asarray(waveform, dtype=np.float32).reshape(-1)
    if source_rate <= 0 or target_rate <= 0:
        raise ValueError("sample rates must be positive")
    if source_rate == target_rate or waveform.size == 0:
        return np.ascontiguousarray(waveform)
    factor = gcd(int(source_rate), int(target_rate))
    result = resample_poly(
        waveform.astype(np.float64, copy=False),
        target_rate // factor,
        source_rate // factor,
    )
    return np.ascontiguousarray(result, dtype=np.float32)
