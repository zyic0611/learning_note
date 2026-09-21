"""Train speaker-disjoint CNN or SVM cross-validation models."""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import tempfile
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .config import (
    ARTIFACT_DIR,
    CACHE_DIR,
    EMOTIONS,
    FEATURE_CACHE_VERSION,
    N_FOLDS,
    NUM_CLASSES,
    SEED,
)
from .data.splits import speaker_folds
from .evaluate import classification_metrics, load_cache, metrics_with_corpora


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.use_deterministic_algorithms(True, warn_only=True)
    except ImportError:
        pass


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _sample_weights(labels: np.ndarray) -> np.ndarray:
    counts = np.bincount(labels, minlength=NUM_CLASSES)
    weights = np.zeros(NUM_CLASSES, dtype=np.float32)
    present = counts > 0
    weights[present] = labels.size / (present.sum() * counts[present])
    return weights


def _fit_svm_fold(
    features: np.ndarray,
    labels: np.ndarray,
    split: dict[str, list[int]],
    *,
    seed: int,
    output: Path,
) -> tuple[np.ndarray, dict[str, Any]]:
    import joblib

    from .models.svm import build_svm

    model = build_svm(seed=seed)
    train = np.asarray(split["train"])
    validation = np.asarray(split["val"])
    test = np.asarray(split["test"])
    model.fit(features[train], labels[train])
    validation_probabilities = _complete_probabilities(model, features[validation])
    test_probabilities = _complete_probabilities(model, features[test])
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "format_version": 1,
            "model_type": "svm",
            "model": model,
            "emotions": EMOTIONS,
        },
        output,
    )
    return test_probabilities, {
        "val": classification_metrics(labels[validation], validation_probabilities),
        "test": classification_metrics(labels[test], test_probabilities),
    }


def _complete_probabilities(model: Any, features: np.ndarray) -> np.ndarray:
    probabilities = model.predict_proba(features)
    completed = np.zeros((len(features), NUM_CLASSES), dtype=np.float64)
    completed[:, np.asarray(model.classes_, dtype=int)] = probabilities
    return completed


def _fit_cnn_fold(
    features: np.ndarray,
    labels: np.ndarray,
    split: dict[str, list[int]],
    *,
    seed: int,
    output: Path,
    resume_path: Path,
    epochs: int,
    patience: int,
    batch_size: int,
    workers: int,
    device_name: str,
) -> tuple[np.ndarray, dict[str, Any]]:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset

    from .models.cnn import SERConvNet, mixup_batch, mixup_loss, spec_augment

    device = torch.device(device_name)
    model = SERConvNet().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=2)
    train_indices = np.asarray(split["train"])
    val_indices = np.asarray(split["val"])
    test_indices = np.asarray(split["test"])
    class_weights = torch.from_numpy(_sample_weights(labels[train_indices])).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(
        TensorDataset(torch.from_numpy(features[train_indices]), torch.from_numpy(labels[train_indices])),
        batch_size=batch_size,
        shuffle=True,
        num_workers=workers,
        generator=generator,
    )
    start_epoch, best_uar, stale = 0, -1.0, 0
    best_state: dict[str, Any] | None = None
    if resume_path.exists():
        state = torch.load(resume_path, map_location=device, weights_only=False)
        model.load_state_dict(state["model_state"])
        optimizer.load_state_dict(state["optimizer_state"])
        start_epoch = int(state["epoch"]) + 1
        best_uar = float(state["best_uar"])
        stale = int(state.get("stale", 0))
        best_state = state.get("best_state")
    history: list[dict[str, Any]] = []
    if start_epoch >= epochs and best_state is None:
        raise ValueError("resume checkpoint has no best model and already reached --epochs")
    for epoch in range(start_epoch, epochs):
        model.train()
        losses: list[float] = []
        for batch_features, batch_labels in loader:
            batch_features = spec_augment(batch_features, generator=generator).to(device)
            batch_labels = batch_labels.to(device)
            mixed, first, second, lam = mixup_batch(
                batch_features, batch_labels, alpha=0.2, generator=generator
            )
            optimizer.zero_grad(set_to_none=True)
            loss = mixup_loss(criterion, model(mixed), first, second, lam)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
        validation_probabilities = _cnn_probabilities(
            model, features[val_indices], device, batch_size
        )
        validation_metrics = classification_metrics(labels[val_indices], validation_probabilities)
        score = float(validation_metrics["uar"] or 0.0)
        scheduler.step(score)
        history.append(
            {
                "epoch": epoch + 1,
                "loss": float(np.mean(losses)),
                "val_uar": score,
            }
        )
        if score > best_uar + 1e-6:
            best_uar = score
            stale = 0
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
        else:
            stale += 1
        resume_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "epoch": epoch,
                "model_state": model.state_dict(),
                "optimizer_state": optimizer.state_dict(),
                "best_state": best_state,
                "best_uar": best_uar,
                "stale": stale,
            },
            resume_path,
        )
        if stale >= patience:
            break
    if best_state is None:
        raise RuntimeError("CNN training completed without a checkpoint")
    model.load_state_dict(best_state)
    validation_probabilities = _cnn_probabilities(model, features[val_indices], device, batch_size)
    test_probabilities = _cnn_probabilities(model, features[test_indices], device, batch_size)
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "format_version": 1,
            "model_type": "cnn",
            "state_dict": best_state,
            "emotions": EMOTIONS,
            "architecture": "SERConvNet",
        },
        output,
    )
    return test_probabilities, {
        "epochs_completed": len(history),
        "best_epoch": int(np.argmax([row["val_uar"] for row in history]) + 1) if history else start_epoch,
        "history": history,
        "val": classification_metrics(labels[val_indices], validation_probabilities),
        "test": classification_metrics(labels[test_indices], test_probabilities),
    }


def _cnn_probabilities(model: Any, features: np.ndarray, device: Any, batch_size: int) -> np.ndarray:
    import torch

    model.eval()
    batches: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(features), batch_size):
            values = torch.from_numpy(features[start : start + batch_size]).to(device)
            batches.append(torch.softmax(model(values), dim=1).cpu().numpy())
    return np.concatenate(batches) if batches else np.empty((0, NUM_CLASSES), dtype=np.float32)


def _select_folds(specification: str, total: int) -> list[int]:
    if specification.lower() == "all":
        return list(range(total))
    selected = sorted({int(value) for value in specification.split(",") if value.strip()})
    if not selected or selected[0] < 0 or selected[-1] >= total:
        raise ValueError(f"--folds must be 'all' or comma-separated indices in [0, {total - 1}]")
    return selected


def _copy_best_artifact(fold_results: list[dict[str, Any]], output_dir: Path, model_type: str) -> Path:
    best = max(fold_results, key=lambda result: result["val"]["uar"] or -1.0)
    source = Path(best["artifact"])
    suffix = ".joblib" if model_type == "svm" else ".pt"
    destination = output_dir / f"best-{model_type}{suffix}"
    temporary = destination.with_name(destination.name + ".part")
    shutil.copy2(source, temporary)
    temporary.replace(destination)
    return destination


def train(args: argparse.Namespace) -> dict[str, Any]:
    seed_everything(args.seed)
    arrays, metadata = load_cache(args.cache)
    labels = np.asarray(arrays["labels"], dtype=np.int64)
    all_splits = speaker_folds(metadata, n_folds=args.n_folds, seed=args.seed)
    selected = _select_folds(args.folds, args.n_folds)
    if args.smoke:
        args.epochs = min(args.epochs, 1)
        args.patience = 1
        args.batch_size = min(args.batch_size, 8)
        selected = selected[:1]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_of_fold = np.full((len(labels), NUM_CLASSES), np.nan, dtype=np.float64)
    fold_results: list[dict[str, Any]] = []
    for fold in selected:
        split = all_splits[fold]
        suffix = ".joblib" if args.model == "svm" else ".pt"
        artifact = args.output_dir / f"{args.model}-fold-{fold}{suffix}"
        if args.model == "svm":
            probabilities, result = _fit_svm_fold(
                arrays["handcrafted"], labels, split, seed=args.seed + fold, output=artifact
            )
        else:
            probabilities, result = _fit_cnn_fold(
                arrays["mel"],
                labels,
                split,
                seed=args.seed + fold,
                output=artifact,
                resume_path=args.output_dir / f"cnn-fold-{fold}.resume.pt",
                epochs=args.epochs,
                patience=args.patience,
                batch_size=args.batch_size,
                workers=args.workers,
                device_name=args.device,
            )
        test_indices = np.asarray(split["test"])
        out_of_fold[test_indices] = probabilities
        result.update(
            {
                "fold": fold,
                "artifact": str(artifact),
                "sizes": {name: len(values) for name, values in split.items()},
            }
        )
        fold_results.append(result)
    evaluated = np.flatnonzero(np.isfinite(out_of_fold).all(axis=1))
    aggregate = metrics_with_corpora(
        labels[evaluated], out_of_fold[evaluated], [metadata[int(index)] for index in evaluated]
    )
    best_artifact = _copy_best_artifact(fold_results, args.output_dir, args.model)
    report = {
        "model_type": args.model,
        "seed": args.seed,
        "n_folds": args.n_folds,
        "folds_run": selected,
        "cache": str(args.cache),
        "best_artifact": str(best_artifact),
        "selection": "highest validation UAR across fold-specific models",
        "per_fold": fold_results,
        "out_of_fold": aggregate,
    }
    _save_json(args.output_dir / f"metrics-{args.model}.json", report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=("cnn", "svm"), required=True)
    parser.add_argument("--cache", type=Path, default=CACHE_DIR / f"features-{FEATURE_CACHE_VERSION}.npz")
    parser.add_argument("--output-dir", type=Path, default=ARTIFACT_DIR)
    parser.add_argument("--folds", default="all", help="all or comma-separated zero-based folds")
    parser.add_argument("--n-folds", type=int, default=N_FOLDS)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--patience", type=int, default=7)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--device", default="cpu", help="PyTorch device for CNN training")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--smoke", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = train(args)
    print(json.dumps({"best_artifact": report["best_artifact"], "out_of_fold": report["out_of_fold"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
