import unittest

import numpy as np

from ser.audio.mel import log_mel_spectrogram, pad_or_crop
from ser.config import N_MELS, SAMPLE_RATE, WINDOW_FRAMES


class MelFrontendTest(unittest.TestCase):
    def test_shape_dtype_and_finiteness(self) -> None:
        time = np.arange(SAMPLE_RATE * 2, dtype=np.float32) / SAMPLE_RATE
        waveform = 0.2 * np.sin(2 * np.pi * 220.0 * time)
        features = log_mel_spectrogram(waveform)
        self.assertEqual(features.shape, (N_MELS, WINDOW_FRAMES))
        self.assertEqual(features.dtype, np.float32)
        self.assertTrue(np.isfinite(features).all())

    def test_inference_is_deterministic(self) -> None:
        waveform = np.random.default_rng(7).normal(size=SAMPLE_RATE * 5).astype(np.float32)
        first = log_mel_spectrogram(waveform)
        second = log_mel_spectrogram(waveform)
        np.testing.assert_array_equal(first, second)

    def test_seeded_training_crop_is_deterministic(self) -> None:
        waveform = np.arange(SAMPLE_RATE * 5, dtype=np.float32)
        first = pad_or_crop(waveform, training=True, rng=np.random.default_rng(42))
        second = pad_or_crop(waveform, training=True, rng=np.random.default_rng(42))
        np.testing.assert_array_equal(first, second)
        self.assertEqual(first.size, SAMPLE_RATE * 3)

    def test_silence_is_finite(self) -> None:
        features = log_mel_spectrogram(np.zeros(0, dtype=np.float32))
        self.assertTrue(np.isfinite(features).all())
        np.testing.assert_allclose(features, np.zeros_like(features), atol=1e-7)


if __name__ == "__main__":
    unittest.main()
