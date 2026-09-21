"""Dataset acquisition and preparation."""

from .labels import Metadata, parse_metadata
from .splits import speaker_folds

__all__ = ["Metadata", "parse_metadata", "speaker_folds"]
