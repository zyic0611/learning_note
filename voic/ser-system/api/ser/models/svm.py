"""Handcrafted-feature RBF SVM."""

from __future__ import annotations

from typing import Any


def build_svm(*, c: float = 10.0, gamma: str | float = "scale", seed: int = 1337) -> Any:
    """Create a leakage-safe scaler plus probabilistic RBF SVM pipeline."""
    try:
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.svm import SVC
    except ImportError as error:
        raise ImportError("scikit-learn is required for the SVM model") from error
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "svm",
                SVC(
                    C=c,
                    gamma=gamma,
                    kernel="rbf",
                    probability=True,
                    class_weight="balanced",
                    random_state=seed,
                ),
            ),
        ]
    )


create_pipeline = build_svm
