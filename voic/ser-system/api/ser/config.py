"""Shared constants for the SER system."""

from pathlib import Path

# --- Audio frontend ---------------------------------------------------------
SAMPLE_RATE = 16000
N_FFT = 512
WIN_LENGTH = 400
HOP_LENGTH = 160
N_MELS = 64
FMIN = 20.0
FMAX = 8000.0
PREEMPH = 0.97

# 3 s window -> 1 + (48000 - 512) // 160 = 297 frames. Rounded up to a fixed
# 300 so the CNN always sees one tensor shape (constant shapes keep CPU
# training fast and make train/serve windows identical).
WINDOW_FRAMES = 300
CLIP_SECONDS = 3.0
MIN_STD = 1e-5

# --- Labels -----------------------------------------------------------------
EMOTIONS = ["neutral", "happy", "sad", "angry", "fear", "disgust"]
NUM_CLASSES = len(EMOTIONS)
LABEL_TO_IDX = {name: i for i, name in enumerate(EMOTIONS)}

# RAVDESS is the only corpus with calm/surprised; keeping them would make those
# classes corpus-identifiable, so they are dropped.
RAVDESS_EMOTION_MAP = {
    "01": "neutral",
    "03": "happy",
    "04": "sad",
    "05": "angry",
    "06": "fear",
    "07": "disgust",
    # "02": calm, "08": surprised -> dropped
}

# --- Data layout ------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path("/data")
RAW_DIR = DATA_DIR / "raw"
CACHE_DIR = DATA_DIR / "cache"
ARTIFACT_DIR = ROOT / "artifacts"

FEATURE_CACHE_VERSION = "v1"

# --- Training ---------------------------------------------------------------
N_FOLDS = 5
SEED = 1337
