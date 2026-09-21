"""Load trained SER artifacts and predict from waveforms."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .audio.io import load_audio
from .audio.mel import log_mel_spectrogram
from .config import EMOTIONS, NUM_CLASSES, SAMPLE_RATE
from .features.handcrafted import extract_handcrafted


class SERPredictor:
    def __init__(self, payload: dict[str, Any], path: Path) -> None:
        self.payload = payload
        self.path = path
        self.model_type = str(payload.get("model_type", ""))
        emotions = list(payload.get("emotions", EMOTIONS))
        if emotions != EMOTIONS:
            raise ValueError(f"artifact label order does not match runtime: {emotions}")
        if self.model_type == "cnn":
            import torch

            from .models.cnn import SERConvNet

            self._torch = torch
            self.model = SERConvNet(num_classes=NUM_CLASSES)
            self.model.load_state_dict(payload["state_dict"])
            self.model.eval()
        elif self.model_type == "svm":
            self.model = payload["model"]
        else:
            raise ValueError(f"unsupported artifact model_type: {self.model_type!r}")

    def predict_cached(
        self,
        *,
        mel: np.ndarray | None = None,
        handcrafted: np.ndarray | None = None,
    ) -> np.ndarray:
        """Predict from the feature representation required by this artifact."""
        if self.model_type == "cnn":
            if mel is None:
                raise ValueError("CNN prediction requires mel features")
            values = np.asarray(mel, dtype=np.float32)
            if values.ndim == 2:
                values = values[None, ...]
            with self._torch.no_grad():
                logits = self.model(self._torch.from_numpy(values))
                return self._torch.softmax(logits, dim=1).numpy()
        if handcrafted is None:
            raise ValueError("SVM prediction requires handcrafted features")
        values = np.asarray(handcrafted, dtype=np.float32)
        if values.ndim == 1:
            values = values[None, ...]
        partial = self.model.predict_proba(values)
        probabilities = np.zeros((values.shape[0], NUM_CLASSES), dtype=np.float64)
        probabilities[:, np.asarray(self.model.classes_, dtype=int)] = partial
        return probabilities

    def predict_proba(
        self,
        waveform: np.ndarray,
        sample_rate: int = SAMPLE_RATE,
    ) -> np.ndarray:
        """Predict one emotion distribution from a mono waveform."""
        samples = np.asarray(waveform, dtype=np.float32)
        if samples.ndim != 1:
            raise ValueError("waveform must be mono")
        if sample_rate != SAMPLE_RATE:
            from .audio.resample import resample_audio

            samples = resample_audio(samples, sample_rate, SAMPLE_RATE)
        if self.model_type == "cnn":
            probabilities = self.predict_cached(mel=log_mel_spectrogram(samples))
        else:
            probabilities = self.predict_cached(handcrafted=extract_handcrafted(samples))
        return probabilities[0]

    def predict(self, waveform: np.ndarray, sample_rate: int = SAMPLE_RATE) -> dict[str, Any]:
        probabilities = self.predict_proba(waveform, sample_rate)
        winner = int(np.argmax(probabilities))
        return {
            "emotion": EMOTIONS[winner],
            "confidence": float(probabilities[winner]),
            "probabilities": {
                emotion: float(probabilities[index]) for index, emotion in enumerate(EMOTIONS)
            },
        }

    def predict_file(self, source: str | Path | bytes) -> dict[str, Any]:
        waveform, sample_rate = load_audio(source)
        return self.predict(waveform, sample_rate)


def _resolve_artifact(path: str | Path) -> Path:
    artifact = Path(path)
    if artifact.is_dir():
        candidates = sorted(artifact.glob("best-*.pt")) + sorted(artifact.glob("best-*.joblib"))
        if len(candidates) != 1:
            raise ValueError(f"artifact directory must contain exactly one best model, found {len(candidates)}")
        artifact = candidates[0]
    if not artifact.is_file():
        raise FileNotFoundError(artifact)
    return artifact


def load_model(path: str | Path) -> SERPredictor:
    """Load a CNN .pt or SVM .joblib artifact on CPU."""
    artifact = _resolve_artifact(path)
    if artifact.suffix == ".pt":
        try:
            import torch
        except ImportError as error:
            raise ImportError("PyTorch is required to load CNN artifacts") from error
        try:
            payload = torch.load(artifact, map_location="cpu", weights_only=False)
        except TypeError:  # PyTorch < 2.6
            payload = torch.load(artifact, map_location="cpu")
    elif artifact.suffix == ".joblib":
        try:
            import joblib
        except ImportError as error:
            raise ImportError("joblib is required to load SVM artifacts") from error
        payload = joblib.load(artifact)
    else:
        raise ValueError("artifact extension must be .pt or .joblib")
    if not isinstance(payload, dict):
        raise ValueError("invalid model artifact payload")
    return SERPredictor(payload, artifact)


load = load_model
