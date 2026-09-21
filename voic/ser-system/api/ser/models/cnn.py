"""Compact log-mel CNN and training augmentations."""

from __future__ import annotations

import numpy as np

try:
    import torch
    from torch import nn
except ImportError as error:  # Keep data-only modules importable without torch.
    raise ImportError("PyTorch is required for ser.models.cnn") from error

from ..config import NUM_CLASSES


class SERConvNet(nn.Module):
    """A 350K-parameter CNN for [batch, 1, 64, 300] log-mel tensors."""

    def __init__(self, num_classes: int = NUM_CLASSES, dropout: float = 0.3) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 24, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(24),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(24, 48, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(48),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(48, 96, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(96),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(96, 128, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((2, 4)),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(dropout),
            nn.Linear(128 * 2 * 4, 192),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(192, num_classes),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        if features.ndim == 3:
            features = features.unsqueeze(1)
        if features.ndim != 4:
            raise ValueError("CNN input must have shape [batch, 64, 300] or [batch, 1, 64, 300]")
        return self.classifier(self.features(features))


SmallCNN = SERConvNet


def spec_augment(
    features: torch.Tensor,
    *,
    frequency_masks: int = 2,
    time_masks: int = 2,
    max_frequency_width: int = 8,
    max_time_width: int = 30,
    generator: torch.Generator | None = None,
) -> torch.Tensor:
    """Apply in-place-free frequency/time masking to a batch."""
    squeeze = features.ndim == 3
    if squeeze:
        features = features.unsqueeze(1)
    if features.ndim != 4:
        raise ValueError("features must be 3D or 4D")
    output = features.clone()
    batch, _, frequency_bins, time_steps = output.shape
    for item in range(batch):
        for _ in range(frequency_masks):
            width = int(torch.randint(max_frequency_width + 1, (1,), generator=generator).item())
            width = min(width, frequency_bins)
            if width:
                start = int(torch.randint(frequency_bins - width + 1, (1,), generator=generator).item())
                output[item, :, start : start + width, :] = 0
        for _ in range(time_masks):
            width = int(torch.randint(max_time_width + 1, (1,), generator=generator).item())
            width = min(width, time_steps)
            if width:
                start = int(torch.randint(time_steps - width + 1, (1,), generator=generator).item())
                output[item, :, :, start : start + width] = 0
    return output.squeeze(1) if squeeze else output


def mixup_batch(
    features: torch.Tensor,
    targets: torch.Tensor,
    *,
    alpha: float = 0.2,
    generator: torch.Generator | None = None,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]:
    """Mix a batch and return mixed input, both targets and lambda."""
    if alpha <= 0 or features.shape[0] < 2:
        return features, targets, targets, 1.0
    if generator is None:
        lam = float(np.random.beta(alpha, alpha))
    else:
        seed = int(torch.randint(2**31 - 1, (1,), generator=generator).item())
        lam = float(np.random.default_rng(seed).beta(alpha, alpha))
    if generator is None:
        permutation = torch.randperm(features.shape[0], device=features.device)
    else:
        permutation = torch.randperm(features.shape[0], generator=generator).to(features.device)
    return lam * features + (1.0 - lam) * features[permutation], targets, targets[permutation], lam


def mixup_loss(
    criterion: nn.Module,
    logits: torch.Tensor,
    first_targets: torch.Tensor,
    second_targets: torch.Tensor,
    lam: float,
) -> torch.Tensor:
    return lam * criterion(logits, first_targets) + (1.0 - lam) * criterion(logits, second_targets)
