#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

docker compose up --build --detach api web

docker compose exec -T api python - <<'PY'
import json
import time
import urllib.error
import urllib.request

base = "http://127.0.0.1:8000/api"
last_error = None
for _ in range(60):
    try:
        health = json.load(urllib.request.urlopen(base + "/health", timeout=3))
        break
    except Exception as exc:
        last_error = exc
        time.sleep(1)
else:
    raise SystemExit(f"API did not become healthy: {last_error}")

assert health["status"] in {"ok", "degraded"}
assert isinstance(health["model_ready"], bool)
models = json.load(urllib.request.urlopen(base + "/models", timeout=3))
expected = ["neutral", "happy", "sad", "angry", "fear", "disgust"]
assert models["labels"] == expected, models["labels"]
try:
    metrics = json.load(urllib.request.urlopen(base + "/metrics", timeout=3))
    assert metrics["labels"] == expected
except urllib.error.HTTPError as exc:
    assert exc.code == 404, exc.code

print(json.dumps({"health": health, "labels": models["labels"]}, ensure_ascii=False, indent=2))
PY

docker compose exec -T web wget -qO- http://127.0.0.1/api/health >/dev/null
printf 'Smoke test passed: frontend proxy and API contracts are reachable.\n'
