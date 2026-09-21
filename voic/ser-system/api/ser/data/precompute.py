"""Build compact feature caches from Hugging Face parquet shards."""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from ..audio.io import load_audio
from ..audio.mel import log_mel_spectrogram
from ..config import CACHE_DIR, FEATURE_CACHE_VERSION, LABEL_TO_IDX, RAW_DIR
from ..features.handcrafted import FEATURE_NAMES, extract_handcrafted
from .labels import Metadata, parse_metadata


def _audio_source(audio: Any, row: Mapping[str, Any], parquet: Path) -> bytes | Path:
    if isinstance(audio, Mapping):
        payload = audio.get("bytes")
        if payload is not None:
            return bytes(payload)
        audio = audio.get("path")
    if isinstance(audio, (bytes, bytearray, memoryview)):
        return bytes(audio)
    candidate = audio
    if not candidate:
        candidate = next(
            (row.get(key) for key in ("path", "audio_path", "file", "filename") if row.get(key)),
            None,
        )
    if candidate is None:
        raise ValueError("parquet row has no audio bytes or path")
    path = Path(str(candidate))
    if not path.is_absolute():
        options = (parquet.parent / path, parquet.parent.parent / path)
        path = next((option for option in options if option.exists()), options[0])
    return path


def _iter_rows(path: Path, batch_size: int = 64) -> Iterable[tuple[int, dict[str, Any]]]:
    try:
        import pyarrow.parquet as pq
    except ImportError as error:
        raise RuntimeError("pyarrow is required to precompute parquet data") from error
    parquet = pq.ParquetFile(path)
    row_index = 0
    for batch in parquet.iter_batches(batch_size=batch_size):
        for row in batch.to_pylist():
            yield row_index, row
            row_index += 1


def _corpus_hint(path: Path) -> str | None:
    lower = str(path).lower()
    if "ravdess" in lower:
        return "ravdess"
    if "crema" in lower:
        return "crema-d"
    return None


def discover_parquets(inputs: Iterable[str | Path]) -> list[Path]:
    files: list[Path] = []
    for value in inputs:
        path = Path(value)
        if path.is_dir():
            files.extend(path.rglob("*.parquet"))
        elif path.suffix.lower() == ".parquet":
            files.append(path)
        else:
            raise ValueError(f"not a parquet file or directory: {path}")
    unique = sorted({path.resolve() for path in files})
    if not unique:
        raise FileNotFoundError("no parquet shards found")
    return unique


def _write_metadata(records: list[Metadata], json_path: Path, csv_path: Path) -> None:
    rows = [record.to_dict() for record in records]
    json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    fieldnames = list(rows[0]) if rows else []
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_cache(
    parquets: Iterable[str | Path],
    output: str | Path,
    *,
    limit: int | None = None,
    crema_majority_threshold: float | None = None,
) -> Path:
    """Decode rows and atomically write mel/handcrafted/label arrays plus sidecars."""
    paths = discover_parquets(parquets)
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    mel_features: list[np.ndarray] = []
    handcrafted: list[np.ndarray] = []
    labels: list[int] = []
    metadata: list[Metadata] = []
    skipped = 0
    for parquet in paths:
        hint = _corpus_hint(parquet)
        for row_index, row in _iter_rows(parquet):
            record = parse_metadata(
                row,
                corpus=hint,
                row_index=row_index,
                source=parquet,
                crema_majority_threshold=crema_majority_threshold,
            )
            if record is None:
                skipped += 1
                continue
            waveform, _ = load_audio(_audio_source(row.get("audio"), row, parquet))
            mel_features.append(log_mel_spectrogram(waveform))
            handcrafted.append(extract_handcrafted(waveform))
            labels.append(LABEL_TO_IDX[record.emotion])
            metadata.append(record)
            if limit is not None and len(metadata) >= limit:
                break
        if limit is not None and len(metadata) >= limit:
            break
    if not metadata:
        raise RuntimeError("no supported labelled audio rows were found")
    mel_array = np.stack(mel_features).astype(np.float32, copy=False)
    handcrafted_array = np.stack(handcrafted).astype(np.float32, copy=False)
    labels_array = np.asarray(labels, dtype=np.int64)
    identifiers = np.asarray([record.sample_id for record in metadata], dtype=np.str_)
    buffer = io.BytesIO()
    np.savez_compressed(
        buffer,
        version=np.asarray(FEATURE_CACHE_VERSION),
        mel=mel_array,
        handcrafted=handcrafted_array,
        labels=labels_array,
        sample_ids=identifiers,
        feature_names=np.asarray(FEATURE_NAMES),
    )
    temporary = destination.with_name(destination.name + ".part")
    temporary.write_bytes(buffer.getvalue())
    temporary.replace(destination)
    _write_metadata(
        metadata,
        destination.with_suffix(".metadata.json"),
        destination.with_suffix(".metadata.csv"),
    )
    print(f"cached {len(metadata)} rows ({skipped} unsupported/ambiguous labels skipped)")
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", type=Path, default=[RAW_DIR])
    parser.add_argument("--output", type=Path, default=CACHE_DIR / f"features-{FEATURE_CACHE_VERSION}.npz")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--crema-majority-threshold",
        type=float,
        help="optional high-agreement subset: require top perceived-vote proportion >= this value",
    )
    args = parser.parse_args(argv)
    build_cache(
        args.inputs,
        args.output,
        limit=args.limit,
        crema_majority_threshold=args.crema_majority_threshold,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
