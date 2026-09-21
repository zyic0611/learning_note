# 支持 Docker Desktop for Mac 的 Intel (amd64) 和 Apple Silicon (arm64)。
# 不固定 platform，让 Docker 自动选择当前机器架构的基础镜像和 Python wheel。
# PYTHON_IMAGE 仅用于无法访问 Docker Hub 的内网环境；Mac 默认使用官方镜像。
ARG PYTHON_IMAGE=python:3.11-slim-bookworm
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8088

# ffmpeg 用于读取 MP3/FLAC/M4A 等格式；WAV 可由 Python 标准库直接读取。
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8088

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8088'), timeout=2)" || exit 1

CMD ["python", "app.py", "--host", "0.0.0.0"]
