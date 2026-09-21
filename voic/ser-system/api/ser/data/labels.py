"""Corpus label and speaker parsing."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from ..config import EMOTIONS, RAVDESS_EMOTION_MAP

_EMOTION_ALIASES = {
    "neu": "neutral",
    "neutral": "neutral",
    "hap": "happy",
    "happy": "happy",
    "happiness": "happy",
    "sad": "sad",
    "sadness": "sad",
    "ang": "angry",
    "anger": "angry",
    "angry": "angry",
    "fea": "fear",
    "fear": "fear",
    "fearful": "fear",
    "dis": "disgust",
    "disgust": "disgust",
    "disgusted": "disgust",
}
_CREMA_VOTE_FIELDS = tuple(EMOTIONS)


@dataclass(frozen=True)
class Metadata:
    sample_id: str
    corpus: str
    speaker: str
    emotion: str
    gender: str | None = None
    source_file: str | None = None
    row_index: int | None = None
    perceived_emotion: str | None = None
    perceived_confidence: float | None = None
    intended_agreement: float | None = None
    vote_angry: float | None = None
    vote_sad: float | None = None
    vote_disgust: float | None = None
    vote_fear: float | None = None
    vote_neutral: float | None = None
    vote_happy: float | None = None

    @property
    def speaker_id(self) -> str:
        return f"{self.corpus.lower()}:{self.speaker}"

    def to_dict(self) -> dict[str, Any]:
        record = asdict(self)
        record["speaker_id"] = self.speaker_id
        return record


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value).strip()


def _normalise_emotion(value: Any) -> str | None:
    token = _text(value).lower().replace("-", "_").split("_")[0]
    if token.isdigit():
        return RAVDESS_EMOTION_MAP.get(token.zfill(2))
    return _EMOTION_ALIASES.get(token)


def _normalise_gender(value: Any) -> str | None:
    token = _text(value).lower()
    if token in {"m", "male", "man"}:
        return "male"
    if token in {"f", "female", "woman"}:
        return "female"
    return token or None


def _source_name(row: Mapping[str, Any]) -> str:
    for key in ("file", "filename", "file_name", "path", "audio_path"):
        value = row.get(key)
        if value:
            return _text(value)
    audio = row.get("audio")
    if isinstance(audio, Mapping) and audio.get("path"):
        return _text(audio["path"])
    return ""


def _ravdess_parts(filename: str) -> tuple[str | None, str | None]:
    stem = Path(filename).stem
    actor = re.search(r"actor[_\s-]?(\d{1,2})", stem, flags=re.IGNORECASE)
    match = re.search(
        r"(?:actor\d{1,2}-)?\d{2}-\d{2}-(0[1-8])-\d{2}-\d{2}-\d{2}-(\d{2})$",
        stem,
        flags=re.IGNORECASE,
    )
    if match:
        speaker = actor.group(1).zfill(2) if actor else match.group(2)
        return match.group(1), speaker
    return None, actor.group(1).zfill(2) if actor else None


def parse_ravdess(row: Mapping[str, Any], row_index: int | None = None) -> Metadata | None:
    filename = _source_name(row)
    file_emotion, file_actor = _ravdess_parts(filename)
    emotion = _normalise_emotion(row.get("emotion")) or _normalise_emotion(file_emotion)
    if emotion not in EMOTIONS:
        return None
    speaker_value = next(
        (_text(row[key]) for key in ("speaker_id", "speaker", "actor", "actor_id") if row.get(key) is not None),
        file_actor or "",
    )
    speaker_match = re.search(r"(\d{1,3})$", speaker_value)
    speaker = speaker_match.group(1).zfill(2) if speaker_match else speaker_value
    if not speaker:
        raise ValueError(f"cannot derive RAVDESS speaker from {filename!r}")
    sample_id = f"ravdess:{Path(filename).stem or row_index}"
    return Metadata(
        sample_id=sample_id,
        corpus="ravdess",
        speaker=speaker,
        emotion=emotion,
        gender=_normalise_gender(row.get("gender")),
        source_file=filename or None,
        row_index=row_index,
    )


def _crema_votes(row: Mapping[str, Any]) -> tuple[dict[str, float], str | None, float | None, bool]:
    votes: dict[str, float] = {}
    for label in _CREMA_VOTE_FIELDS:
        try:
            value = float(row[label])
            if np.isfinite(value):
                votes[label] = value
        except (KeyError, TypeError, ValueError):
            pass
    if not votes:
        return votes, None, None, False
    best_value = max(votes.values())
    winners = [label for label, value in votes.items() if value == best_value]
    return votes, winners[0] if len(winners) == 1 else None, best_value, len(winners) == 1


def _crema_emotion(row: Mapping[str, Any], filename: str) -> str | None:
    """Return CREMA-D's intended/file-code label, not its perception vote mode."""
    intended = _normalise_emotion(row.get("major_emotion"))
    if intended is not None:
        return intended
    parts = Path(filename).stem.split("_")
    return _normalise_emotion(parts[2]) if len(parts) >= 3 else None


def parse_crema_d(
    row: Mapping[str, Any],
    row_index: int | None = None,
    *,
    require_unique_argmax: bool = False,
    majority_threshold: float | None = None,
) -> Metadata | None:
    filename = _source_name(row)
    emotion = _crema_emotion(row, filename)
    if emotion not in EMOTIONS:
        return None
    votes, perceived, agreement, unique = _crema_votes(row)
    if require_unique_argmax and votes and not unique:
        return None
    if majority_threshold is not None:
        if not 0.0 <= majority_threshold <= 1.0:
            raise ValueError("majority_threshold must be between zero and one")
        if agreement is None or agreement < majority_threshold:
            return None
    stem = Path(filename).stem
    file_speaker = stem.split("_", 1)[0] if "_" in stem else ""
    speaker = next(
        (_text(row[key]) for key in ("speaker_id", "speaker", "actor", "actor_id") if row.get(key) is not None),
        file_speaker,
    )
    if not speaker:
        raise ValueError(f"cannot derive CREMA-D speaker from {filename!r}")
    sample_id = f"crema-d:{stem or row_index}"
    return Metadata(
        sample_id=sample_id,
        corpus="crema-d",
        speaker=speaker,
        emotion=emotion,
        gender=_normalise_gender(row.get("gender")),
        source_file=filename or None,
        row_index=row_index,
        perceived_emotion=perceived,
        perceived_confidence=agreement,
        intended_agreement=votes.get(emotion),
        vote_angry=votes.get("angry"),
        vote_sad=votes.get("sad"),
        vote_disgust=votes.get("disgust"),
        vote_fear=votes.get("fear"),
        vote_neutral=votes.get("neutral"),
        vote_happy=votes.get("happy"),
    )


def infer_corpus(row: Mapping[str, Any], source: str | Path | None = None) -> str:
    corpus = _text(row.get("corpus") or row.get("dataset")).lower()
    hint = f"{corpus} {_source_name(row)} {_text(source)}".lower()
    if "crema" in hint or "major_emotion" in row or any(key in row for key in _CREMA_VOTE_FIELDS):
        return "crema-d"
    if "ravdess" in hint or "intensity" in row:
        return "ravdess"
    filename = Path(_source_name(row)).stem
    if re.search(r"\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}", filename):
        return "ravdess"
    if re.match(r"\d+_[A-Z]{3}_[A-Z]{3}_", filename, flags=re.IGNORECASE):
        return "crema-d"
    raise ValueError("cannot infer corpus from row schema or filename")


def parse_metadata(
    row: Mapping[str, Any],
    *,
    corpus: str | None = None,
    row_index: int | None = None,
    source: str | Path | None = None,
    crema_majority_threshold: float | None = None,
) -> Metadata | None:
    """Parse a Hugging Face parquet row, dropping unsupported/ambiguous labels."""
    name = (corpus or infer_corpus(row, source)).lower().replace("_", "-")
    if "ravdess" in name:
        return parse_ravdess(row, row_index)
    if "crema" in name:
        return parse_crema_d(
            row,
            row_index,
            majority_threshold=crema_majority_threshold,
        )
    raise ValueError(f"unsupported corpus: {corpus}")
