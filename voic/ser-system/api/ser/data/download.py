"""Download the fixed SER parquet sources safely."""

from __future__ import annotations

import argparse
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from ..config import RAW_DIR

RAVDESS_URL = "https://huggingface.co/datasets/AbstractTTS/RAVDESS/resolve/main/data/train-00000-of-00001.parquet"
CREMA_D_URLS = (
    "https://huggingface.co/datasets/AbstractTTS/CREMA-D/resolve/main/data/train-00000-of-00002.parquet",
    "https://huggingface.co/datasets/AbstractTTS/CREMA-D/resolve/main/data/train-00001-of-00002.parquet",
)
URLS = (RAVDESS_URL, *CREMA_D_URLS)
_EXPECTED_MIN_BYTES = {
    RAVDESS_URL: 100_000_000,
    CREMA_D_URLS[0]: 250_000_000,
    CREMA_D_URLS[1]: 250_000_000,
}


def destination_for(url: str, output_dir: str | Path = RAW_DIR) -> Path:
    if url not in URLS:
        raise ValueError("only the configured RAVDESS and CREMA-D parquet URLs are allowed")
    corpus = "ravdess" if url == RAVDESS_URL else "crema-d"
    return Path(output_dir) / corpus / url.rsplit("/", 1)[-1]


def _valid_parquet(path: Path, minimum: int) -> bool:
    if not path.is_file() or path.stat().st_size < minimum:
        return False
    with path.open("rb") as handle:
        if handle.read(4) != b"PAR1":
            return False
        handle.seek(-4, os.SEEK_END)
        return handle.read(4) == b"PAR1"


def _candidate_urls(url: str) -> tuple[str, ...]:
    mirror = url.replace("https://huggingface.co/", "https://hf-mirror.com/", 1)
    return url, mirror


def download_file(
    url: str,
    output_dir: str | Path = RAW_DIR,
    *,
    retries: int = 3,
    timeout: int = 120,
) -> Path:
    """Download a known parquet atomically without replacing valid data."""
    target = destination_for(url, output_dir)
    minimum = _EXPECTED_MIN_BYTES[url]
    if _valid_parquet(target, minimum):
        return target
    if target.exists():
        raise ValueError(f"refusing to overwrite invalid existing file: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    last_error: Exception | None = None
    for attempt in range(max(1, retries)):
        for candidate in _candidate_urls(url):
            try:
                request = urllib.request.Request(
                    candidate,
                    headers={"User-Agent": "ser-system/1.0", "Accept": "application/octet-stream"},
                )
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    status = getattr(response, "status", 200)
                    if status < 200 or status >= 300:
                        raise RuntimeError(f"HTTP {status} for {candidate}")
                    length = response.headers.get("Content-Length")
                    if length is not None and int(length) < minimum:
                        raise RuntimeError(f"response too small ({length} bytes) for {candidate}")
                    with part.open("wb") as handle:
                        while True:
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            handle.write(chunk)
                        handle.flush()
                        os.fsync(handle.fileno())
                if not _valid_parquet(part, minimum):
                    raise RuntimeError(f"download is not a complete parquet file: {candidate}")
                part.replace(target)
                return target
            except (OSError, RuntimeError, urllib.error.URLError, urllib.error.HTTPError) as error:
                last_error = error
                part.unlink(missing_ok=True)
        if attempt + 1 < retries:
            time.sleep(2**attempt)
    raise RuntimeError(f"failed to download {url}: {last_error}")


def download_all(output_dir: str | Path = RAW_DIR) -> list[Path]:
    return [download_file(url, output_dir) for url in URLS]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=RAW_DIR)
    args = parser.parse_args(argv)
    for path in download_all(args.output_dir):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
