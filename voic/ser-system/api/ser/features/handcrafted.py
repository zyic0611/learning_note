"""Fixed-dimensional deterministic acoustic feature vector."""

from __future__ import annotations

import numpy as np
from scipy.fft import dct

from ..audio.mel import mel_filterbank, pad_or_crop
from ..config import HOP_LENGTH, N_FFT, N_MELS, SAMPLE_RATE, WIN_LENGTH

_BASE_NAMES = (
    ["f0_hz", "voicing"]
    + ["rms", "log_energy", "zcr"]
    + [f"mfcc_{index:02d}" for index in range(13)]
    + [f"mfcc_delta_{index:02d}" for index in range(13)]
    + ["spectral_centroid_hz", "spectral_flux", "spectral_rolloff85_hz"]
)
_STATS = ("mean", "std", "min", "max")
FEATURE_NAMES = tuple(f"{name}_{stat}" for name in _BASE_NAMES for stat in _STATS)
FEATURE_DIM = len(FEATURE_NAMES)  # 136


def _frame_waveform(waveform: np.ndarray) -> np.ndarray:
    count = 1 + max(0, (waveform.size - WIN_LENGTH) // HOP_LENGTH)
    frames = np.zeros((count, WIN_LENGTH), dtype=np.float64)
    for index in range(count):
        start = index * HOP_LENGTH
        part = waveform[start : start + WIN_LENGTH]
        frames[index, : part.size] = part
    return frames


def _f0_autocorrelation(frames: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    minimum_lag = max(1, SAMPLE_RATE // 500)
    maximum_lag = min(frames.shape[1] - 1, SAMPLE_RATE // 60)
    f0 = np.zeros(frames.shape[0], dtype=np.float64)
    voicing = np.zeros_like(f0)
    for index, frame in enumerate(frames):
        centered = frame - frame.mean()
        energy = np.dot(centered, centered)
        if energy <= 1e-10:
            continue
        autocorr = np.correlate(centered, centered, mode="full")[frame.size - 1 :]
        segment = autocorr[minimum_lag : maximum_lag + 1]
        lag = minimum_lag + int(np.argmax(segment))
        strength = autocorr[lag] / max(autocorr[0], 1e-12)
        voicing[index] = max(0.0, strength)
        if strength >= 0.3:
            f0[index] = SAMPLE_RATE / lag
    return f0, voicing


def _delta(values: np.ndarray) -> np.ndarray:
    padded = np.pad(values, ((2, 2), (0, 0)), mode="edge")
    return (2 * (padded[4:] - padded[:-4]) + padded[3:-1] - padded[1:-3]) / 10.0


def _aggregate(values: np.ndarray) -> np.ndarray:
    output: list[float] = []
    for column in range(values.shape[1]):
        series = values[:, column]
        output.extend((series.mean(), series.std(), series.min(), series.max()))
    return np.nan_to_num(np.asarray(output, dtype=np.float32))


def extract_handcrafted(waveform: np.ndarray) -> np.ndarray:
    """Extract 136 aggregate prosodic, cepstral and spectral features."""
    x = pad_or_crop(np.asarray(waveform, dtype=np.float32), training=False)
    frames = _frame_waveform(x)
    windowed = frames * np.hanning(WIN_LENGTH)
    padded = np.pad(windowed, ((0, 0), (0, N_FFT - WIN_LENGTH)))
    magnitude = np.abs(np.fft.rfft(padded, n=N_FFT, axis=1))
    power = magnitude**2 / N_FFT
    frequencies = np.fft.rfftfreq(N_FFT, 1.0 / SAMPLE_RATE)
    magnitude_sum = np.maximum(magnitude.sum(axis=1), 1e-12)

    f0, voicing = _f0_autocorrelation(frames)
    rms = np.sqrt(np.mean(frames**2, axis=1) + 1e-12)
    log_energy = np.log(np.sum(frames**2, axis=1) + 1e-10)
    zcr = np.mean(np.abs(np.diff(np.signbit(frames), axis=1)), axis=1)

    mel_energy = power @ mel_filterbank().T.astype(np.float64)
    log_mel = np.log(np.maximum(mel_energy, 1e-10))
    mfcc = dct(log_mel, type=2, axis=1, norm="ortho")[:, :13]
    mfcc_delta = _delta(mfcc)

    centroid = (magnitude * frequencies).sum(axis=1) / magnitude_sum
    normalized = magnitude / magnitude_sum[:, None]
    flux = np.zeros(frames.shape[0])
    if frames.shape[0] > 1:
        flux[1:] = np.sqrt(np.sum(np.diff(normalized, axis=0) ** 2, axis=1))
    cumulative = np.cumsum(power, axis=1)
    threshold = 0.85 * cumulative[:, -1]
    rolloff = frequencies[np.argmax(cumulative >= threshold[:, None], axis=1)]

    frame_features = np.column_stack(
        (f0, voicing, rms, log_energy, zcr, mfcc, mfcc_delta, centroid, flux, rolloff)
    )
    result = _aggregate(frame_features)
    if result.shape != (FEATURE_DIM,):
        raise AssertionError(f"feature contract violated: {result.shape}")
    return result


extract_features = extract_handcrafted
