"""Evaluation utilities and artifact evaluation CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .config import CACHE_DIR, EMOTIONS, FEATURE_CACHE_VERSION


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, classes: int = len(EMOTIONS)) -> np.ndarray:
    matrix = np.zeros((classes, classes), dtype=np.int64)
    for truth, prediction in zip(np.asarray(y_true, dtype=int), np.asarray(y_pred, dtype=int)):
        if 0 <= truth < classes and 0 <= prediction < classes:
            matrix[truth, prediction] += 1
    return matrix


def classification_metrics(y_true: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
    truth = np.asarray(y_true, dtype=np.int64)
    scores = np.asarray(probabilities, dtype=np.float64)
    if truth.ndim != 1 or scores.shape != (truth.size, len(EMOTIONS)):
        raise ValueError("probabilities must have shape [samples, num_classes]")
    predictions = scores.argmax(axis=1)
    matrix = confusion_matrix(truth, predictions)
    true_support = matrix.sum(axis=1)
    predicted_support = matrix.sum(axis=0)
    true_positives = np.diag(matrix).astype(np.float64)
    recalls = np.divide(
        true_positives,
        true_support,
        out=np.full(len(EMOTIONS), np.nan, dtype=float),
        where=true_support > 0,
    )
    precisions = np.divide(
        true_positives,
        predicted_support,
        out=np.zeros(len(EMOTIONS), dtype=float),
        where=predicted_support > 0,
    )
    f1_scores = np.zeros(len(EMOTIONS), dtype=float)
    denominators = precisions + np.nan_to_num(recalls, nan=0.0)
    np.divide(
        2.0 * precisions * np.nan_to_num(recalls, nan=0.0),
        denominators,
        out=f1_scores,
        where=denominators > 0,
    )
    present = true_support > 0
    return {
        "samples": int(truth.size),
        "accuracy": float(np.mean(predictions == truth)) if truth.size else None,
        "uar": float(np.mean(recalls[present])) if np.any(present) else None,
        "macro_f1": float(np.mean(f1_scores[present])) if np.any(present) else None,
        "confusion_matrix": matrix.tolist(),
        "per_class_precision": {
            emotion: (float(precisions[index]) if present[index] else None)
            for index, emotion in enumerate(EMOTIONS)
        },
        "per_class_recall": {
            emotion: (float(recalls[index]) if present[index] else None)
            for index, emotion in enumerate(EMOTIONS)
        },
        "per_class_f1": {
            emotion: (float(f1_scores[index]) if present[index] else None)
            for index, emotion in enumerate(EMOTIONS)
        },
        "support": {emotion: int(true_support[index]) for index, emotion in enumerate(EMOTIONS)},
    }


def metrics_with_corpora(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    metadata: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    result = classification_metrics(y_true, probabilities)
    result["per_corpus"] = {}
    if metadata is not None:
        corpora = sorted({str(record.get("corpus", "unknown")) for record in metadata})
        for corpus in corpora:
            indices = [index for index, record in enumerate(metadata) if str(record.get("corpus", "unknown")) == corpus]
            result["per_corpus"][corpus] = classification_metrics(
                np.asarray(y_true)[indices], np.asarray(probabilities)[indices]
            )
    return result


def load_cache(cache_path: str | Path) -> tuple[dict[str, np.ndarray], list[dict[str, Any]]]:
    path = Path(cache_path)
    with np.load(path, allow_pickle=False) as archive:
        arrays = {name: archive[name] for name in archive.files}
    metadata_path = path.with_suffix(".metadata.json")
    if not metadata_path.exists():
        raise FileNotFoundError(f"metadata sidecar not found: {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    count = len(arrays["labels"])
    if len(metadata) != count:
        raise ValueError(f"cache has {count} samples but metadata has {len(metadata)} rows")
    return arrays, metadata


def evaluate_artifact(
    artifact_path: str | Path,
    cache_path: str | Path,
    indices: Sequence[int] | None = None,
) -> dict[str, Any]:
    from .registry import load_model

    arrays, metadata = load_cache(cache_path)
    chosen = np.arange(len(arrays["labels"])) if indices is None else np.asarray(indices, dtype=np.int64)
    predictor = load_model(artifact_path)
    probabilities = predictor.predict_cached(
        mel=arrays.get("mel", np.empty(0))[chosen] if "mel" in arrays else None,
        handcrafted=arrays.get("handcrafted", np.empty(0))[chosen] if "handcrafted" in arrays else None,
    )
    return metrics_with_corpora(
        arrays["labels"][chosen], probabilities, [metadata[int(index)] for index in chosen]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument(
        "--cache",
        type=Path,
        default=CACHE_DIR / f"features-{FEATURE_CACHE_VERSION}.npz",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    metrics = evaluate_artifact(args.artifact, args.cache)
    text = json.dumps(metrics, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
