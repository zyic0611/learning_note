#!/usr/bin/env bash
# Mac/Linux 一键入口：只要求安装 Docker Desktop。
set -euo pipefail

cd "$(dirname "$0")"

usage() {
  cat <<'EOF'
相似歌曲检索系统 - Docker 入口

用法：
  bash docker.sh start                 构建并启动网页（默认）
  bash docker.sh stop                  停止服务
  bash docker.sh logs                  查看日志
  bash docker.sh test                  运行 18 项数学自检
  bash docker.sh search <歌名>          命令行检索，如：钢琴-01
  bash docker.sh rebuild-index         重新扫描 data/songs 并建库
  bash docker.sh evaluate              重新计算全库评估指标
  bash docker.sh demo-reset            重新生成 48 首演示曲、建库并评估

网页地址：http://localhost:8088
EOF
}

need_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "错误：未找到 Docker。请先在 Mac 安装并启动 Docker Desktop："
    echo "https://www.docker.com/products/docker-desktop/"
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    echo "错误：Docker 没有运行。请打开 Docker Desktop，等它启动完成后重试。"
    exit 1
  fi
}

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    echo "错误：找不到 docker compose。请升级 Docker Desktop。"
    exit 1
  fi
}

run_python() {
  # 用临时容器执行，挂载当前 data/out；不依赖网页服务是否已启动。
  compose run --rm --no-deps mir python "$@"
}

cmd="${1:-start}"
case "$cmd" in
  start)
    need_docker
    compose up -d --build --force-recreate
    echo
    echo "启动成功：http://localhost:8088"
    echo "如果浏览器没有自动打开，请手动复制这个地址。"
    ;;
  stop)
    need_docker
    compose down
    ;;
  logs)
    need_docker
    compose logs -f mir
    ;;
  test)
    need_docker
    run_python tests/test_basic.py
    ;;
  search)
    need_docker
    if [[ $# -lt 2 ]]; then
      echo "用法：bash docker.sh search <歌曲名>"
      echo "示例：bash docker.sh search 钢琴-01"
      exit 1
    fi
    run_python -m mirtool.search --query "$2"
    ;;
  rebuild-index)
    need_docker
    run_python scripts/build_index.py
    run_python scripts/evaluate.py --recompute --skip-if-unlabeled
    echo "特征库已更新；有完整 family 标签时评估指标也会同步更新。请运行 bash docker.sh start 重启网页。"
    ;;
  evaluate)
    need_docker
    run_python scripts/evaluate.py --recompute --skip-if-unlabeled
    ;;
  demo-reset)
    need_docker
    run_python scripts/make_demo_library.py
    run_python scripts/build_index.py
    run_python scripts/evaluate.py --recompute --skip-if-unlabeled
    echo "演示库已重建。运行 bash docker.sh start 打开网页。"
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "未知命令：$cmd"
    usage
    exit 1
    ;;
esac
