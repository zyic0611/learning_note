"""NumPy log-mel frontend shared by training and inference."""

from functools import lru_cache

import numpy as np

from ..config import (
    CLIP_SECONDS,
    FMAX,
    FMIN,
    HOP_LENGTH,
    MIN_STD,
    N_FFT,
    N_MELS,
    PREEMPH,
    SAMPLE_RATE,
    WINDOW_FRAMES,
    WIN_LENGTH,
)


def pad_or_crop(
    waveform: np.ndarray,
    *,
    training: bool = False,
    rng: np.random.Generator | None = None,
    sample_rate: int = SAMPLE_RATE,
    seconds: float = CLIP_SECONDS,
) -> np.ndarray:
    """Pad/crop to a fixed window; center at inference, random crop at training."""
    x = np.asarray(waveform, dtype=np.float32)
    if x.ndim != 1:
        raise ValueError("waveform must be mono with shape [samples]")
    target = int(round(sample_rate * seconds))
    if target <= 0:
        raise ValueError("target window must contain samples")
    if x.size < target:
        missing = target - x.size
        left = missing // 2
        return np.pad(x, (left, missing - left)).astype(np.float32, copy=False)
    if x.size == target:
        return np.ascontiguousarray(x)
    if training:
        generator = rng if rng is not None else np.random.default_rng()
        start = int(generator.integers(0, x.size - target + 1))
    else:
        start = (x.size - target) // 2
    return np.ascontiguousarray(x[start : start + target])


def _hz_to_mel(freq: np.ndarray | float) -> np.ndarray:
    return 2595.0 * np.log10(1.0 + np.asarray(freq) / 700.0)


def _mel_to_hz(mel: np.ndarray) -> np.ndarray:
    return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)


@lru_cache(maxsize=8)
def mel_filterbank(
    sample_rate: int = SAMPLE_RATE,
    n_fft: int = N_FFT,
    n_mels: int = N_MELS,
    fmin: float = FMIN,
    fmax: float = FMAX,
) -> np.ndarray:
    """Create an unnormalized HTK triangular mel filter bank."""
    if not (0 <= fmin < fmax <= sample_rate / 2):
        raise ValueError("mel frequency range must lie within Nyquist")
    mel_edges = np.linspace(_hz_to_mel(fmin), _hz_to_mel(fmax), n_mels + 2)
    hz_edges = _mel_to_hz(mel_edges)
    frequencies = np.fft.rfftfreq(n_fft, 1.0 / sample_rate)
    bank = np.zeros((n_mels, frequencies.size), dtype=np.float64)
    for index, (left, center, right) in enumerate(
        zip(hz_edges[:-2], hz_edges[1:-1], hz_edges[2:])
    ):
        bank[index] = np.maximum(
            0.0,
            np.minimum(
                (frequencies - left) / max(center - left, np.finfo(float).eps),
                (right - frequencies) / max(right - center, np.finfo(float).eps),
            ),
        )
    return bank.astype(np.float32)


def _frames(x: np.ndarray) -> np.ndarray:
    if x.size < N_FFT:
        x = np.pad(x, (0, N_FFT - x.size))
    count = 1 + (x.size - N_FFT) // HOP_LENGTH
    shape = (count, N_FFT)
    strides = (x.strides[0] * HOP_LENGTH, x.strides[0])
    return np.lib.stride_tricks.as_strided(x, shape=shape, strides=strides).copy()


def log_mel_spectrogram(
    waveform: np.ndarray,
    *,
    training: bool = False,
    rng: np.random.Generator | None = None,
    eps: float = 1e-10,
) -> np.ndarray:
    """Convert a 16 kHz mono waveform to CMVN log-mel features [64, 300]."""
    if eps <= 0:
        raise ValueError("eps must be positive")
    x = pad_or_crop(waveform, training=training, rng=rng)
    emphasized = np.empty_like(x)
    if x.size:
        emphasized[0] = x[0]
        emphasized[1:] = x[1:] - PREEMPH * x[:-1]
    frames = _frames(emphasized).astype(np.float64, copy=False)
    window = np.zeros(N_FFT, dtype=np.float64)
    window_offset = (N_FFT - WIN_LENGTH) // 2
    window[window_offset : window_offset + WIN_LENGTH] = np.hanning(WIN_LENGTH)
    power = np.abs(np.fft.rfft(frames * window, n=N_FFT, axis=1)) ** 2
    power /= N_FFT
    mel = mel_filterbank().astype(np.float64) @ power.T
    features = np.log(np.maximum(mel, eps))
    mean = features.mean(axis=1, keepdims=True)
    std = np.maximum(features.std(axis=1, keepdims=True), MIN_STD)
    features = (features - mean) / std
    if features.shape[1] < WINDOW_FRAMES:
        features = np.pad(features, ((0, 0), (0, WINDOW_FRAMES - features.shape[1])))
    elif features.shape[1] > WINDOW_FRAMES:
        features = features[:, :WINDOW_FRAMES]
    return np.ascontiguousarray(features, dtype=np.float32)


# Friendly aliases for callers that use frontend/feature naming.
extract_log_mel = log_mel_spectrogram
waveform_to_log_mel = log_mel_spectrogram
