#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

model="${1:-cnn}"
if [[ "$model" != "cnn" && "$model" != "svm" ]]; then
  printf '用法: %s [cnn|svm]\n' "$0" >&2
  exit 2
fi

HOST_UID="$(id -u)" HOST_GID="$(id -g)" \
  docker compose --profile training run --rm \
  --entrypoint python \
  -e EXPORT_MODEL="$model" \
  trainer -c '
import json
import os
import shutil
from pathlib import Path

root = Path("/app/artifacts")
model = os.environ["EXPORT_MODEL"]
suffix = ".pt" if model == "cnn" else ".joblib"
source_model = root / f"best-{model}{suffix}"
source_metrics = root / f"metrics-{model}.json"
if not source_model.is_file() or not source_metrics.is_file():
    raise SystemExit(f"missing training outputs: {source_model} or {source_metrics}")
active = root / "active"
if active.exists():
    shutil.rmtree(active)
active.mkdir(parents=True)
shutil.copy2(source_model, active / source_model.name)
payload = json.loads(source_metrics.read_text(encoding="utf-8"))
(root / "metrics.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"serving artifact: {active / source_model.name}")
print(f"metrics: {root / '"'"'metrics.json'"'"'}")
'

printf '导出完成。运行 ./scripts/up.sh 使 API 加载新产物。\n'
