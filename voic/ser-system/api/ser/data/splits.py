"""Deterministic speaker-disjoint cross-validation splits."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from ..config import N_FOLDS, SEED


def _get(record: Any, key: str, default: Any = None) -> Any:
    if isinstance(record, Mapping):
        return record.get(key, default)
    return getattr(record, key, default)


def _speaker(record: Any) -> str:
    explicit = _get(record, "speaker_id")
    if explicit:
        return str(explicit)
    corpus = str(_get(record, "corpus", "unknown")).lower()
    speaker = _get(record, "speaker")
    if speaker is None:
        raise ValueError("every sample requires speaker or speaker_id")
    return f"{corpus}:{speaker}"


def _stratum(record: Any) -> str:
    corpus = str(_get(record, "corpus", "unknown")).lower()
    gender = _get(record, "gender")
    return f"{corpus}|{str(gender).lower() if gender else 'unknown'}"


def _assign_speakers(metadata: Sequence[Any], n_folds: int, seed: int) -> list[set[str]]:
    if n_folds < 2:
        raise ValueError("n_folds must be at least two")
    by_speaker: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(metadata):
        by_speaker[_speaker(record)].append(index)
    if len(by_speaker) < n_folds:
        raise ValueError("number of unique speakers must be at least n_folds")
    speaker_strata: dict[str, str] = {}
    for speaker, indices in by_speaker.items():
        counts = Counter(_stratum(metadata[index]) for index in indices)
        speaker_strata[speaker] = sorted(counts, key=lambda key: (-counts[key], key))[0]

    generator = np.random.default_rng(seed)
    tie_break = {speaker: float(generator.random()) for speaker in by_speaker}
    groups: dict[str, list[str]] = defaultdict(list)
    for speaker, stratum in speaker_strata.items():
        groups[stratum].append(speaker)
    folds = [set() for _ in range(n_folds)]
    fold_samples = np.zeros(n_folds, dtype=np.int64)
    fold_strata = [Counter() for _ in range(n_folds)]
    for stratum in sorted(groups, key=lambda value: (-len(groups[value]), value)):
        speakers = sorted(
            groups[stratum],
            key=lambda speaker: (-len(by_speaker[speaker]), tie_break[speaker], speaker),
        )
        for speaker in speakers:
            candidates = sorted(
                range(n_folds),
                key=lambda fold: (
                    fold_strata[fold][stratum],
                    fold_samples[fold],
                    len(folds[fold]),
                    fold,
                ),
            )
            chosen = candidates[0]
            folds[chosen].add(speaker)
            fold_samples[chosen] += len(by_speaker[speaker])
            fold_strata[chosen][stratum] += 1
    return folds


def speaker_folds(
    metadata: Sequence[Any],
    *,
    n_folds: int = N_FOLDS,
    seed: int = SEED,
) -> list[dict[str, list[int]]]:
    """Return train/val/test indices with each speaker testing exactly once."""
    records = list(metadata)
    test_speakers = _assign_speakers(records, n_folds, seed)
    all_speakers = set().union(*test_speakers)
    if sum(len(group) for group in test_speakers) != len(all_speakers):
        raise AssertionError("a speaker was assigned to multiple test folds")
    output: list[dict[str, list[int]]] = []
    for fold in range(n_folds):
        test_group = test_speakers[fold]
        val_group = test_speakers[(fold + 1) % n_folds]
        train_group = all_speakers - test_group - val_group
        split = {"train": [], "val": [], "test": []}
        for index, record in enumerate(records):
            speaker = _speaker(record)
            bucket = "test" if speaker in test_group else "val" if speaker in val_group else "train"
            split[bucket].append(index)
        sets = {name: {_speaker(records[index]) for index in values} for name, values in split.items()}
        assert sets["train"].isdisjoint(sets["val"])
        assert sets["train"].isdisjoint(sets["test"])
        assert sets["val"].isdisjoint(sets["test"])
        assert sum(len(values) for values in split.values()) == len(records)
        output.append(split)
    test_counts = Counter(_speaker(records[index]) for split in output for index in split["test"])
    sample_counts = Counter(_speaker(record) for record in records)
    assert test_counts == sample_counts, "every speaker/sample must occur in exactly one test fold"
    return output


make_splits = speaker_folds
