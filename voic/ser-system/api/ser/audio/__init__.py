"""Audio decoding and feature extraction."""

from .io import load_audio
from .mel import log_mel_spectrogram, pad_or_crop
from .resample import resample_audio

__all__ = ["load_audio", "log_mel_spectrogram", "pad_or_crop", "resample_audio"]
