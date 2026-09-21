"""Lazy faster-whisper integration which never prevents SER from starting."""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any

import numpy as np

LOGGER = logging.getLogger(__name__)


class ASRService:
    """Load faster-whisper on first use and expose a failure-tolerant API."""

    def __init__(self) -> None:
        self._model: Any | None = None
        self._load_attempted = False
        self._error: str | None = None
        self._load_lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return self._model is not None

    @property
    def status(self) -> str:
        if self.ready:
            return "ready"
        if self._error:
            return f"unavailable: {self._error}"
        return "not_loaded"

    def _load(self) -> Any | None:
        if self._load_attempted:
            return self._model
        with self._load_lock:
            if self._load_attempted:
                return self._model
            self._load_attempted = True
            if os.getenv("ASR_ENABLED", "true").lower() not in {"1", "true", "yes"}:
                self._error = "disabled"
                return None
            builtin_path = Path(os.getenv("BUILTIN_ASR_MODEL_PATH", "/opt/asr-model"))
            model_ref = os.getenv("ASR_MODEL_PATH") or (
                str(builtin_path) if builtin_path.is_dir() else os.getenv("ASR_MODEL", "small")
            )
            local_only = os.getenv("ASR_LOCAL_ONLY", "false").lower() in {"1", "true", "yes"}
            cache_dir = Path(os.getenv("ASR_CACHE_DIR", "/data/models/whisper"))
            try:
                from faster_whisper import WhisperModel

                cache_dir.mkdir(parents=True, exist_ok=True)
                self._model = WhisperModel(
                    model_ref,
                    device="cpu",
                    compute_type="int8",
                    download_root=str(cache_dir),
                    local_files_only=local_only,
                    cpu_threads=max(1, int(os.getenv("ASR_CPU_THREADS", "4"))),
                    num_workers=1,
                )
            except Exception as exc:  # ASR is explicitly optional at runtime.
                self._error = f"{type(exc).__name__}: {exc}"
                LOGGER.warning("ASR unavailable: %s", self._error)
            return self._model

    def transcribe(self, audio: np.ndarray, language: str | None = None) -> dict[str, Any]:
        model = self._load()
        if model is None:
            return {
                "text": "",
                "language": language,
                "segments": [],
                "available": False,
                "detail": self.status,
            }
        try:
            segments_iter, info = model.transcribe(
                np.asarray(audio, dtype=np.float32),
                language=language or None,
                beam_size=1,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            segments = [
                {"start": round(float(item.start), 3), "end": round(float(item.end), 3), "text": item.text.strip()}
                for item in segments_iter
            ]
            text = " ".join(item["text"] for item in segments if item["text"]).strip()
            return {
                "text": text,
                "language": getattr(info, "language", language),
                "segments": segments,
                "available": True,
                "detail": None,
            }
        except Exception as exc:
            LOGGER.warning("ASR transcription failed: %s", exc)
            return {
                "text": "",
                "language": language,
                "segments": [],
                "available": False,
                "detail": f"transcription failed: {type(exc).__name__}",
            }
