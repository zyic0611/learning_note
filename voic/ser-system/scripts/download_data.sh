#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

HOST_UID="$(id -u)" HOST_GID="$(id -g)" \
  docker compose --profile training run --rm trainer ser.data.download --output-dir /data/raw
