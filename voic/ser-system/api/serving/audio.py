"""Safe decoding and lightweight visualisation helpers."""

from __future__ import annotations

import math
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from ser.config import FMAX, FMIN, HOP_LENGTH, N_FFT, N_MELS, SAMPLE_RATE, WIN_LENGTH

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".webm"}
SUPPORTED_CONTENT_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/x-m4a",
    "audio/webm",
    "video/webm",  # MediaRecorder commonly labels an audio-only WebM this way.
    "application/octet-stream",
}


class AudioDecodeError(ValueError):
    pass


def validate_upload_type(filename: str | None, content_type: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise AudioDecodeError("仅支持 wav、mp3、m4a、webm 音频")
    mime = (content_type or "").split(";", 1)[0].strip().lower()
    if mime and mime not in SUPPORTED_CONTENT_TYPES:
        raise AudioDecodeError(f"不支持的 Content-Type: {mime}")
    return suffix


def decode_audio(data: bytes, suffix: str, *, max_duration_seconds: float) -> tuple[np.ndarray, int]:
    """Decode untrusted media through ffmpeg without invoking a shell."""

    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="ser-upload-", suffix=suffix, delete=False) as handle:
            handle.write(data)
            temp_path = handle.name
        command = [
            "ffmpeg",
            "-v",
            "error",
            "-nostdin",
            "-i",
            temp_path,
            "-map",
            "0:a:0",
            "-ac",
            "1",
            "-ar",
            str(SAMPLE_RATE),
            "-t",
            str(max_duration_seconds + 0.25),
            "-f",
            "f32le",
            "pipe:1",
        ]
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=max(30.0, min(180.0, max_duration_seconds * 2.0)),
        )
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", errors="replace").strip()[-500:]
            raise AudioDecodeError(f"音频解码失败: {detail or 'ffmpeg error'}")
        audio = np.frombuffer(result.stdout, dtype="<f4").astype(np.float32, copy=True)
    except FileNotFoundError as exc:
        raise AudioDecodeError("服务器缺少 ffmpeg") from exc
    except subprocess.TimeoutExpired as exc:
        raise AudioDecodeError("音频解码超时") from exc
    finally:
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass

    if audio.size == 0:
        raise AudioDecodeError("音频为空或没有可解码的音轨")
    duration = audio.size / SAMPLE_RATE
    if duration > max_duration_seconds:
        raise AudioDecodeError(f"音频时长不能超过 {max_duration_seconds:g} 秒")
    return np.clip(audio, -1.0, 1.0), SAMPLE_RATE


def downsample_waveform(audio: np.ndarray, max_points: int = 800) -> dict[str, Any]:
    samples = np.asarray(audio, dtype=np.float32).reshape(-1)
    if samples.size == 0:
        return {"min": [], "max": []}
    bucket_count = min(max_points, samples.size)
    edges = np.linspace(0, samples.size, bucket_count + 1, dtype=np.int64)
    minimum: list[float] = []
    maximum: list[float] = []
    for start, end in zip(edges[:-1], edges[1:]):
        bucket = samples[start : max(start + 1, end)]
        minimum.append(round(float(np.min(bucket)), 5))
        maximum.append(round(float(np.max(bucket)), 5))
    return {"min": minimum, "max": maximum}


def _hz_to_mel(frequency: np.ndarray | float) -> np.ndarray:
    return 2595.0 * np.log10(1.0 + np.asarray(frequency) / 700.0)


def _mel_to_hz(mels: np.ndarray) -> np.ndarray:
    return 700.0 * (np.power(10.0, mels / 2595.0) - 1.0)


def _mel_filter_bank(sample_rate: int) -> np.ndarray:
    upper = min(float(FMAX), sample_rate / 2.0)
    mel_points = np.linspace(_hz_to_mel(FMIN), _hz_to_mel(upper), N_MELS + 2)
    bins = np.floor((N_FFT + 1) * _mel_to_hz(mel_points) / sample_rate).astype(int)
    bins = np.clip(bins, 0, N_FFT // 2)
    filters = np.zeros((N_MELS, N_FFT // 2 + 1), dtype=np.float32)
    for index in range(N_MELS):
        left, center, right = int(bins[index]), int(bins[index + 1]), int(bins[index + 2])
        center = max(center, left + 1)
        right = max(right, center + 1)
        for frequency_bin in range(left, min(center, filters.shape[1])):
            filters[index, frequency_bin] = (frequency_bin - left) / (center - left)
        for frequency_bin in range(center, min(right, filters.shape[1])):
            filters[index, frequency_bin] = (right - frequency_bin) / (right - center)
    return filters


def mel_heatmap(audio: np.ndarray, sample_rate: int, max_frames: int = 240) -> dict[str, Any]:
    samples = np.asarray(audio, dtype=np.float32).reshape(-1)
    if samples.size < N_FFT:
        samples = np.pad(samples, (0, N_FFT - samples.size))
    frame_count = 1 + math.ceil((samples.size - N_FFT) / HOP_LENGTH)
    padded_size = (frame_count - 1) * HOP_LENGTH + N_FFT
    samples = np.pad(samples, (0, max(0, padded_size - samples.size)))
    shape = (frame_count, N_FFT)
    strides = (samples.strides[0] * HOP_LENGTH, samples.strides[0])
    frames = np.lib.stride_tricks.as_strided(samples, shape=shape, strides=strides, writeable=False)
    window = np.hanning(WIN_LENGTH).astype(np.float32)
    analysis_window = np.zeros(N_FFT, dtype=np.float32)
    start = (N_FFT - WIN_LENGTH) // 2
    analysis_window[start : start + WIN_LENGTH] = window
    power = np.abs(np.fft.rfft(frames * analysis_window, n=N_FFT, axis=1)) ** 2
    mel_power = _mel_filter_bank(sample_rate) @ power.T
    mel_db = 10.0 * np.log10(np.maximum(mel_power, 1e-10))
    peak = float(np.max(mel_db))
    mel_db = np.maximum(mel_db, peak - 80.0)

    if mel_db.shape[1] > max_frames:
        edges = np.linspace(0, mel_db.shape[1], max_frames + 1, dtype=np.int64)
        mel_db = np.stack(
            [np.mean(mel_db[:, start:end], axis=1) for start, end in zip(edges[:-1], edges[1:])],
            axis=1,
        )
    return {
        "n_mels": int(mel_db.shape[0]),
        "n_frames": int(mel_db.shape[1]),
        "hop_seconds": round(HOP_LENGTH / sample_rate, 6),
        "min_db": round(float(np.min(mel_db)), 3),
        "max_db": round(float(np.max(mel_db)), 3),
        "values": np.round(mel_db, 2).tolist(),
    }
