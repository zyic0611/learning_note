ARG PYTHON_IMAGE=python:3.11-slim-bookworm
FROM ${PYTHON_IMAGE} AS base

ARG DOWNLOAD_ASR_MODEL=false
ARG ASR_MODEL=small

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ASR_CACHE_DIR=/data/models/whisper \
    BUILTIN_ASR_MODEL_PATH=/opt/asr-model

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade "pip==24.3.1" \
    && python -m pip install --only-binary=:all: -r requirements.txt

COPY ser ./ser
COPY serving ./serving
COPY artifacts ./artifacts

RUN if [ "$DOWNLOAD_ASR_MODEL" = "true" ]; then \
      python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='Systran/faster-whisper-${ASR_MODEL}', local_dir='/opt/asr-model')"; \
    fi

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data/models/whisper \
    && chown -R appuser:appuser /app /data /opt/asr-model 2>/dev/null || true

FROM base AS trainer
COPY requirements-training.txt ./requirements-training.txt
RUN python -m pip install --only-binary=:all: -r requirements-training.txt
ENTRYPOINT ["python", "-m"]
CMD ["ser.train", "--help"]

FROM base AS runtime
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import json,urllib.request; data=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)); assert data['status'] in ('ok','degraded')"
CMD ["uvicorn", "serving.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
