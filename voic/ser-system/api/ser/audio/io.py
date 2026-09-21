"""Safe audio decoding from paths and in-memory bytes."""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import numpy as np

from ..config import SAMPLE_RATE
from .resample import resample_audio


def _mono_float32(data: np.ndarray) -> np.ndarray:
    samples = np.asarray(data)
    if samples.ndim == 2:
        samples = samples.mean(axis=1)
    if samples.ndim != 1:
        raise ValueError(f"unsupported audio shape: {samples.shape}")
    if np.issubdtype(samples.dtype, np.integer):
        info = np.iinfo(samples.dtype)
        scale = float(max(abs(info.min), info.max))
        samples = samples.astype(np.float32) / scale
    else:
        samples = samples.astype(np.float32, copy=False)
    return np.nan_to_num(samples, copy=False)


def _soundfile_decode(source: str | Path | bytes | bytearray | memoryview) -> tuple[np.ndarray, int]:
    try:
        import soundfile as sf
    except ImportError as error:
        raise RuntimeError("soundfile is unavailable") from error
    handle = io.BytesIO(bytes(source)) if isinstance(source, (bytes, bytearray, memoryview)) else source
    data, rate = sf.read(handle, dtype="float32", always_2d=True)
    return _mono_float32(data), int(rate)


def _ffprobe_rate(source: str | Path | bytes | bytearray | memoryview) -> int:
    is_bytes = isinstance(source, (bytes, bytearray, memoryview))
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=sample_rate",
        "-of",
        "json",
        "pipe:0" if is_bytes else str(Path(source)),
    ]
    result = subprocess.run(
        command,
        input=bytes(source) if is_bytes else None,
        check=True,
        capture_output=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)
    streams = payload.get("streams", [])
    if not streams:
        raise ValueError("input contains no audio stream")
    return int(streams[0]["sample_rate"])


def _ffmpeg_decode(source: str | Path | bytes | bytearray | memoryview) -> tuple[np.ndarray, int]:
    is_bytes = isinstance(source, (bytes, bytearray, memoryview))
    input_name = "pipe:0" if is_bytes else str(Path(source))
    source_rate = _ffprobe_rate(source)
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        input_name,
        "-map",
        "0:a:0",
        "-f",
        "f32le",
        "-acodec",
        "pcm_f32le",
        "-ac",
        "1",
        "-ar",
        str(source_rate),
        "pipe:1",
    ]
    result = subprocess.run(
        command,
        input=bytes(source) if is_bytes else None,
        check=True,
        capture_output=True,
        timeout=60,
    )
    return np.frombuffer(result.stdout, dtype="<f4").copy(), source_rate


def load_audio(
    source: str | Path | bytes | bytearray | memoryview,
    *,
    target_rate: int = SAMPLE_RATE,
) -> tuple[np.ndarray, int]:
    """Decode to mono float32 and resample, preferring soundfile for WAV."""
    try:
        waveform, source_rate = _soundfile_decode(source)
    except (RuntimeError, OSError, ValueError):
        waveform, source_rate = _ffmpeg_decode(source)
    waveform = resample_audio(waveform, source_rate, target_rate)
    return waveform, target_rate


decode_audio = load_audio
