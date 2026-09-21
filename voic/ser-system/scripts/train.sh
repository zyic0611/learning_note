#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

usage() {
  cat <<'USAGE'
用法: ./scripts/train.sh <命令> [参数]

命令:
  precompute [参数]     生成特征缓存
  svm [参数]            训练 SVM（默认全部 fold）
  cnn [参数]            训练 CNN（默认全部 fold）
  smoke [svm|cnn]       单 fold/单 epoch 冒烟训练

示例:
  ./scripts/train.sh precompute
  ./scripts/train.sh svm --folds all
  ./scripts/train.sh cnn --epochs 40 --patience 7
  ./scripts/train.sh smoke cnn
USAGE
}

command_name="${1:-}"
if [[ -z "$command_name" || "$command_name" == "-h" || "$command_name" == "--help" ]]; then
  usage
  exit 0
fi
shift

run_trainer() {
  HOST_UID="$(id -u)" HOST_GID="$(id -g)" \
    docker compose --profile training run --rm trainer "$@"
}

case "$command_name" in
  precompute)
    run_trainer ser.data.precompute /data/raw --output /data/cache/features-v1.npz "$@"
    ;;
  svm)
    run_trainer ser.train --model svm --cache /data/cache/features-v1.npz --output-dir /app/artifacts "$@"
    ;;
  cnn)
    run_trainer ser.train --model cnn --cache /data/cache/features-v1.npz --output-dir /app/artifacts "$@"
    ;;
  smoke)
    model="${1:-cnn}"
    if [[ "$model" != "cnn" && "$model" != "svm" ]]; then
      printf 'smoke 模型必须是 cnn 或 svm\n' >&2
      exit 2
    fi
    shift || true
    run_trainer ser.train --model "$model" --cache /data/cache/features-v1.npz --output-dir /app/artifacts --smoke "$@"
    ;;
  *)
    printf '未知命令: %s\n' "$command_name" >&2
    usage >&2
    exit 2
    ;;
esac
