"""FastAPI entrypoint for file and streaming speech-emotion inference."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from ser.config import ARTIFACT_DIR, CLIP_SECONDS, EMOTIONS, SAMPLE_RATE
from serving.asr import ASRService
from serving.audio import AudioDecodeError, decode_audio, downsample_waveform, mel_heatmap, validate_upload_type
from serving.vad import VADResult, detect_speech

LOGGER = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
MAX_DURATION_SECONDS = float(os.getenv("MAX_DURATION_SECONDS", "300"))
WS_WINDOW_SECONDS = float(os.getenv("WS_WINDOW_SECONDS", "3"))
WS_UPDATE_SECONDS = float(os.getenv("WS_UPDATE_SECONDS", "1"))
WS_MAX_SESSION_SECONDS = float(os.getenv("WS_MAX_SESSION_SECONDS", "7200"))
METRICS_PATH = Path(os.getenv("METRICS_PATH", str(ARTIFACT_DIR / "metrics.json")))
MODEL_ARTIFACT_PATH = Path(os.getenv("SER_ARTIFACT_PATH", str(ARTIFACT_DIR)))


class ModelState:
    def __init__(self) -> None:
        self.recognizer: Any | None = None
        self.error: str | None = None
        self.loaded_artifact: str | None = None
        self.asr = ASRService()
        # faster-whisper and PyTorch CPU work share one lane to avoid contention.
        self.inference_lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return self.recognizer is not None

    def load(self) -> None:
        try:
            from ser import registry

            recognizer_class = getattr(registry, "EmotionRecognizer", None)
            if recognizer_class is not None:
                recognizer = recognizer_class(str(MODEL_ARTIFACT_PATH))
            else:
                # Compatibility with the initial ML implementation; the agreed
                # public interface remains predict_waveform(audio, sample_rate).
                predictor = registry.load_model(MODEL_ARTIFACT_PATH)

                class PredictorAdapter:
                    def predict_waveform(self, audio: np.ndarray, sample_rate: int) -> Any:
                        return predictor.predict(audio, sample_rate)

                recognizer = PredictorAdapter()
            self.recognizer = recognizer
            self.loaded_artifact = str(MODEL_ARTIFACT_PATH)
            self.error = None
            LOGGER.info("SER model loaded from %s", MODEL_ARTIFACT_PATH)
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            LOGGER.warning("SER model is not ready: %s", self.error)


STATE = ModelState()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Loading can involve disk and torch initialisation. The server starts even
    # when this fails, and exposes readiness through /health.
    await run_in_threadpool(STATE.load)
    yield


app = FastAPI(title="Speech Emotion Recognition API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(AudioDecodeError)
async def audio_error_handler(_: Request, exc: AudioDecodeError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc), "code": "invalid_audio"})


def _probability_mapping(raw: Any) -> dict[str, float]:
    source = raw
    if isinstance(raw, Mapping):
        for key in ("probabilities", "probs", "scores"):
            if key in raw:
                source = raw[key]
                break
    if isinstance(source, Mapping):
        values = [float(source.get(label, 0.0)) for label in EMOTIONS]
    elif isinstance(source, np.ndarray):
        values = np.asarray(source, dtype=np.float64).reshape(-1).tolist()
    elif isinstance(source, Sequence) and not isinstance(source, (str, bytes, bytearray)):
        values = [float(value) for value in source]
    else:
        raise ValueError("recognizer result contains no probabilities")
    if len(values) != len(EMOTIONS):
        raise ValueError(f"expected {len(EMOTIONS)} probabilities, got {len(values)}")
    array = np.nan_to_num(np.asarray(values, dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)
    if np.any(array < 0.0) or float(array.sum()) <= 0.0:
        shifted = array - float(np.max(array))
        array = np.exp(shifted)
    total = float(array.sum())
    if total <= 0.0:
        raise ValueError("recognizer returned zero probability mass")
    array /= total
    return {label: round(float(array[index]), 6) for index, label in enumerate(EMOTIONS)}


def _prediction(raw: Any) -> dict[str, Any]:
    probabilities = _probability_mapping(raw)
    label = max(EMOTIONS, key=probabilities.__getitem__)
    return {"label": label, "confidence": probabilities[label], "probabilities": probabilities}


def _silence_prediction() -> dict[str, Any]:
    return {"label": None, "confidence": 0.0, "probabilities": {label: 0.0 for label in EMOTIONS}}


def _invoke_recognizer(audio: np.ndarray, sample_rate: int) -> dict[str, Any]:
    if STATE.recognizer is None:
        raise RuntimeError("SER model is not ready")
    raw = STATE.recognizer.predict_waveform(audio, sample_rate)
    if inspect.isawaitable(raw):
        raise TypeError("predict_waveform must be a synchronous method")
    return _prediction(raw)


def _infer_locked(audio: np.ndarray, sample_rate: int, language: str | None, transcribe: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    with STATE.inference_lock:
        prediction = _invoke_recognizer(audio, sample_rate)
        transcript = (
            STATE.asr.transcribe(audio, language)
            if transcribe
            else {"text": "", "language": language, "segments": [], "available": False, "detail": "disabled_for_request"}
        )
    return prediction, transcript


def _timeline(audio: np.ndarray, sample_rate: int) -> list[dict[str, Any]]:
    """Build non-overlapping 3 s SER segments for an uploaded file."""

    window = max(1, int(CLIP_SECONDS * sample_rate))
    output: list[dict[str, Any]] = []
    for offset in range(0, audio.size, window):
        chunk = audio[offset : offset + window]
        if chunk.size < int(0.25 * sample_rate):
            continue
        vad = detect_speech(chunk, sample_rate)
        if not vad.is_speech:
            output.append(
                {
                    "start": round(offset / sample_rate, 3),
                    "end": round((offset + chunk.size) / sample_rate, 3),
                    "label": None,
                    "confidence": 0.0,
                    "probabilities": {label: 0.0 for label in EMOTIONS},
                    "is_speech": False,
                }
            )
            continue
        prediction = _invoke_recognizer(chunk, sample_rate)
        output.append(
            {
                "start": round(offset / sample_rate, 3),
                "end": round((offset + chunk.size) / sample_rate, 3),
                **prediction,
                "is_speech": True,
            }
        )
    return output


def _aggregate_timeline(timeline: list[dict[str, Any]]) -> dict[str, Any]:
    speech_segments = [segment for segment in timeline if segment["is_speech"]]
    if not speech_segments:
        return _silence_prediction()
    weights = np.asarray(
        [max(float(segment["end"]) - float(segment["start"]), 1e-6) for segment in speech_segments],
        dtype=np.float64,
    )
    values = np.asarray(
        [[float(segment["probabilities"][label]) for label in EMOTIONS] for segment in speech_segments],
        dtype=np.float64,
    )
    probabilities = np.average(values, axis=0, weights=weights)
    return _prediction(probabilities)


def _file_inference(audio: np.ndarray, language: str | None, transcribe: bool) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], VADResult]:
    vad = detect_speech(audio, SAMPLE_RATE)
    with STATE.inference_lock:
        timeline = _timeline(audio, SAMPLE_RATE)
        prediction = _aggregate_timeline(timeline)
        if not vad.is_speech:
            transcript = {
                "text": "",
                "language": language,
                "segments": [],
                "available": STATE.asr.ready,
                "detail": "silence_detected",
            }
        else:
            transcript = (
                STATE.asr.transcribe(audio, language)
                if transcribe
                else {"text": "", "language": language, "segments": [], "available": False, "detail": "disabled_for_request"}
            )
    return prediction, timeline, transcript, vad


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok" if STATE.ready else "degraded",
        "model_ready": STATE.ready,
        "model_error": STATE.error,
        "asr_ready": STATE.asr.ready,
        "asr_status": STATE.asr.status,
    }


@app.get("/api/models")
async def models() -> dict[str, Any]:
    return {
        "labels": list(EMOTIONS),
        "ser": {
            "name": "EmotionRecognizer",
            "ready": STATE.ready,
            "artifact_path": STATE.loaded_artifact,
            "error": STATE.error,
            "sample_rate": SAMPLE_RATE,
            "window_seconds": CLIP_SECONDS,
        },
        "asr": {
            "name": os.getenv("ASR_MODEL", "small"),
            "ready": STATE.asr.ready,
            "status": STATE.asr.status,
            "compute_type": "int8",
            "device": "cpu",
        },
    }


def _metric_value(source: Mapping[str, Any], *names: str) -> float | None:
    for name in names:
        value = source.get(name)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and np.isfinite(value):
            return float(value)
    return None


def _normalize_metrics_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Adapt the trainer report to the stable frontend evaluation contract."""

    aggregate_value = payload.get("out_of_fold", payload.get("metrics", payload))
    aggregate = aggregate_value if isinstance(aggregate_value, Mapping) else {}
    model_name = str(payload.get("model_type", payload.get("model", "SER"))).upper()
    uar = _metric_value(aggregate, "uar", "UAR")
    accuracy = _metric_value(aggregate, "accuracy", "acc")
    macro_f1 = _metric_value(aggregate, "macro_f1", "macroF1", "f1")

    folds: list[dict[str, Any]] = []
    raw_folds = payload.get("per_fold", payload.get("folds", []))
    if isinstance(raw_folds, list):
        for index, item in enumerate(raw_folds):
            if not isinstance(item, Mapping):
                continue
            test_value = item.get("test", item)
            test = test_value if isinstance(test_value, Mapping) else {}
            fold_id = item.get("fold", index)
            folds.append(
                {
                    "fold": f"Fold {fold_id}",
                    "uar": _metric_value(test, "uar", "UAR"),
                    "macroF1": _metric_value(test, "macro_f1", "macroF1", "f1"),
                    "accuracy": _metric_value(test, "accuracy", "acc"),
                }
            )

    confusion = aggregate.get("confusion_matrix", aggregate.get("confusionMatrix", []))
    if not isinstance(confusion, list):
        confusion = []
    per_corpus = aggregate.get("per_corpus", {})
    dataset = " + ".join(str(name) for name in per_corpus) if isinstance(per_corpus, Mapping) else None
    sample_count = aggregate.get("samples", payload.get("sample_count"))
    comparison = payload.get("comparison")
    if not isinstance(comparison, list):
        comparison = [
            {
                "model": model_name,
                "uar": uar,
                "macroF1": macro_f1,
                "accuracy": accuracy,
            }
        ]
    return {
        "labels": list(EMOTIONS),
        "uar": uar,
        "macroF1": macro_f1,
        "accuracy": accuracy,
        "comparison": comparison,
        "confusionMatrix": confusion,
        "folds": folds,
        "dataset": dataset,
        "sampleCount": int(sample_count) if isinstance(sample_count, (int, float)) else None,
        "model": model_name,
        "source": METRICS_PATH.name,
    }


@app.get("/api/metrics")
async def metrics() -> dict[str, Any]:
    if not METRICS_PATH.is_file():
        raise HTTPException(status_code=404, detail="metrics.json 尚未生成，请先训练或导出模型")
    try:
        content = await run_in_threadpool(METRICS_PATH.read_text, "utf-8")
        payload = json.loads(content)
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=f"metrics.json 无法读取: {type(exc).__name__}") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="metrics.json 顶层必须是对象")
    return _normalize_metrics_payload(payload)


async def _read_limited_upload(upload: UploadFile) -> bytes:
    data = bytearray()
    while True:
        chunk = await upload.read(min(1024 * 1024, MAX_UPLOAD_BYTES + 1 - len(data)))
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="上传文件不能超过 25 MB")
    return bytes(data)


@app.post("/api/predict")
async def predict(
    file: UploadFile = File(...),
    language: str | None = None,
    transcribe: bool = True,
) -> dict[str, Any]:
    if not STATE.ready:
        raise HTTPException(status_code=503, detail="情绪识别模型尚未就绪，请先训练或挂载模型产物")
    suffix = validate_upload_type(file.filename, file.content_type)
    try:
        data = await _read_limited_upload(file)
    finally:
        await file.close()
    if not data:
        raise HTTPException(status_code=422, detail="上传文件为空")
    audio, sample_rate = await run_in_threadpool(
        lambda: decode_audio(data, suffix, max_duration_seconds=MAX_DURATION_SECONDS)
    )
    prediction_data, timeline, transcript, vad = await run_in_threadpool(
        _file_inference, audio, language, transcribe
    )
    waveform = await run_in_threadpool(downsample_waveform, audio)
    mel = await run_in_threadpool(mel_heatmap, audio, sample_rate)
    return {
        "labels": list(EMOTIONS),
        "audio": {"duration": round(audio.size / sample_rate, 3), "sample_rate": sample_rate, "is_speech": vad.is_speech},
        "prediction": prediction_data,
        "transcript": transcript,
        "timeline": timeline,
        "waveform": {"sample_rate": sample_rate, **waveform},
        "mel": mel,
    }


def _parse_ws_config(message: dict[str, Any]) -> tuple[str | None, bool]:
    if message.get("type") not in {None, "config"}:
        raise ValueError("首条消息必须是 config JSON")
    if int(message.get("sample_rate", SAMPLE_RATE)) != SAMPLE_RATE:
        raise ValueError("流式音频仅支持 16000 Hz")
    if int(message.get("channels", 1)) != 1:
        raise ValueError("流式音频仅支持单声道")
    if str(message.get("format", "pcm_s16le")).lower() not in {"pcm_s16le", "pcm16"}:
        raise ValueError("流式音频仅支持 PCM16 little-endian")
    language_value = message.get("language")
    language = str(language_value) if language_value else None
    return language, bool(message.get("transcribe", False))


@app.websocket("/api/ws/stream")
async def stream(websocket: WebSocket) -> None:
    await websocket.accept()
    if not STATE.ready:
        await websocket.send_json({"type": "error", "code": "model_not_ready", "detail": "情绪识别模型尚未就绪"})
        await websocket.close(code=1013)
        return

    try:
        config = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
        language, transcribe = _parse_ws_config(config)
    except (asyncio.TimeoutError, ValueError, TypeError, json.JSONDecodeError) as exc:
        await websocket.send_json({"type": "error", "code": "invalid_config", "detail": str(exc)})
        await websocket.close(code=1008)
        return
    except WebSocketDisconnect:
        return

    window_samples = int(WS_WINDOW_SECONDS * SAMPLE_RATE)
    update_samples = int(WS_UPDATE_SECONDS * SAMPLE_RATE)
    max_session_samples = int(WS_MAX_SESSION_SECONDS * SAMPLE_RATE)
    chunks: deque[np.ndarray] = deque()
    buffered_samples = 0
    samples_since_update = 0
    total_samples = 0
    update_id = 0
    await websocket.send_json(
        {
            "type": "ready",
            "sample_rate": SAMPLE_RATE,
            "channels": 1,
            "format": "pcm_s16le",
            "labels": list(EMOTIONS),
            "window_seconds": WS_WINDOW_SECONDS,
            "update_seconds": WS_UPDATE_SECONDS,
        }
    )

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            if message.get("text") is not None:
                try:
                    control = json.loads(message["text"])
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "code": "invalid_control", "detail": "控制消息必须是 JSON"})
                    continue
                if control.get("type") == "stop":
                    await websocket.send_json({"type": "stopped"})
                    break
                if control.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                continue

            payload = message.get("bytes")
            if payload is None:
                continue
            if not payload:
                continue
            if len(payload) % 2:
                await websocket.send_json({"type": "error", "code": "invalid_pcm", "detail": "PCM16 字节数必须为偶数"})
                continue
            pcm = np.frombuffer(payload, dtype="<i2").astype(np.float32) / 32768.0
            chunks.append(pcm)
            buffered_samples += pcm.size
            samples_since_update += pcm.size
            total_samples += pcm.size
            if total_samples > max_session_samples:
                await websocket.send_json({"type": "error", "code": "session_too_long", "detail": "流式会话达到时长上限"})
                await websocket.close(code=1008)
                return
            while chunks and buffered_samples - chunks[0].size >= window_samples:
                buffered_samples -= chunks.popleft().size
            if buffered_samples > window_samples and chunks:
                trim = buffered_samples - window_samples
                chunks[0] = chunks[0][trim:]
                buffered_samples = window_samples
            if samples_since_update < update_samples:
                continue
            samples_since_update %= update_samples
            window = np.concatenate(tuple(chunks))[-window_samples:].copy()
            if window.size < int(0.25 * SAMPLE_RATE):
                continue
            vad = detect_speech(window, SAMPLE_RATE)
            update_id += 1
            end_seconds = total_samples / SAMPLE_RATE
            start_seconds = max(0.0, end_seconds - window.size / SAMPLE_RATE)
            if vad.is_speech:
                prediction_data, transcript = await run_in_threadpool(
                    _infer_locked, window, SAMPLE_RATE, language, transcribe
                )
            else:
                prediction_data = _silence_prediction()
                transcript = {
                    "text": "",
                    "language": language,
                    "segments": [],
                    "available": STATE.asr.ready,
                    "detail": "silence_detected",
                }
            await websocket.send_json(
                {
                    "type": "prediction",
                    "id": update_id,
                    "timestamp": round(time.time(), 3),
                    "labels": list(EMOTIONS),
                    "window": {"start": round(start_seconds, 3), "end": round(end_seconds, 3), "is_speech": vad.is_speech},
                    "prediction": prediction_data,
                    "transcript": transcript,
                    "timeline": [
                        {
                            "start": round(start_seconds, 3),
                            "end": round(end_seconds, 3),
                            **prediction_data,
                            "is_speech": vad.is_speech,
                        }
                    ],
                }
            )
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        LOGGER.exception("WebSocket stream failed")
        try:
            await websocket.send_json({"type": "error", "code": "stream_error", "detail": type(exc).__name__})
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        chunks.clear()
