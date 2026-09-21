"""Small dependency-free energy VAD used to gate SER inference."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class VADResult:
    is_speech: bool
    speech_ratio: float
    rms_dbfs: float
    threshold_dbfs: float


def _dbfs(values: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(values, 1e-8))


def detect_speech(
    audio: np.ndarray,
    sample_rate: int,
    *,
    frame_ms: int = 30,
    absolute_floor_dbfs: float = -52.0,
    min_speech_ratio: float = 0.08,
) -> VADResult:
    """Classify a mono floating-point waveform using adaptive frame energy.

    The adaptive threshold follows the estimated noise floor, while an absolute
    floor prevents digital silence from being classified as speech. This is a
    gate rather than a diarisation-grade VAD, and deliberately has no model
    download or platform-specific binary dependency.
    """

    samples = np.asarray(audio, dtype=np.float32).reshape(-1)
    samples = np.nan_to_num(samples, nan=0.0, posinf=0.0, neginf=0.0)
    if sample_rate <= 0 or samples.size == 0:
        return VADResult(False, 0.0, -160.0, absolute_floor_dbfs)

    frame_size = max(1, int(sample_rate * frame_ms / 1000))
    frame_count = max(1, (samples.size + frame_size - 1) // frame_size)
    padded = np.pad(samples, (0, frame_count * frame_size - samples.size))
    frames = padded.reshape(frame_count, frame_size)
    frame_rms = np.sqrt(np.mean(np.square(frames, dtype=np.float64), axis=1))
    frame_db = _dbfs(frame_rms)

    overall_rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
    overall_db = float(_dbfs(np.asarray([overall_rms]))[0])
    noise_floor = float(np.percentile(frame_db, 20))
    threshold = max(absolute_floor_dbfs, min(-32.0, noise_floor + 10.0))
    speech_ratio = float(np.mean(frame_db >= threshold))

    # A short loud event still needs enough total energy to avoid impulse noise.
    is_speech = overall_db >= absolute_floor_dbfs and speech_ratio >= min_speech_ratio
    return VADResult(is_speech, speech_ratio, overall_db, threshold)
