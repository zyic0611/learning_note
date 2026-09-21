import { EMPTY_PROBABILITIES, normalizeEmotion } from '../constants/emotions';
import type {
  EmotionKey,
  EmotionProbabilities,
  EmotionSegment,
  FoldMetric,
  HealthResponse,
  MelPayload,
  MetricsResponse,
  ModelComparisonRow,
  PredictionResult,
  StreamMessage,
  TranscriptPayload,
  UnknownRecord,
  WaveformPayload,
} from '../types/api';
import { EMOTION_KEYS } from '../types/api';
import { asFiniteNumber, normalizeScore } from '../utils/format';

const API_PREFIX = '/api';

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function unwrap(payload: unknown): UnknownRecord {
  if (!isRecord(payload)) return {};
  for (const key of ['data', 'result']) {
    if (isRecord(payload[key])) return payload[key] as UnknownRecord;
  }
  return payload;
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function asBoolean(value: unknown, fallback = false): boolean {
  return typeof value === 'boolean' ? value : fallback;
}

function asNumberArray(value: unknown): number[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const numbers = value.map((entry) => asFiniteNumber(entry, Number.NaN)).filter(Number.isFinite);
  return numbers.length > 0 ? numbers : undefined;
}

function asMatrix(value: unknown): number[][] | undefined {
  if (!Array.isArray(value)) return undefined;
  const rows = value.map(asNumberArray).filter((row): row is number[] => Boolean(row));
  return rows.length > 0 ? rows : undefined;
}

function parseLabels(value: unknown): EmotionKey[] {
  if (!Array.isArray(value)) return [...EMOTION_KEYS];
  const parsed = value.map(normalizeEmotion).slice(0, EMOTION_KEYS.length);
  const matchesConfiguredLabels = parsed.length === EMOTION_KEYS.length
    && EMOTION_KEYS.every((label) => parsed.includes(label));
  return matchesConfiguredLabels ? parsed : [...EMOTION_KEYS];
}

function parseProbabilities(value: unknown, labels: EmotionKey[] = [...EMOTION_KEYS]): EmotionProbabilities {
  const result: EmotionProbabilities = { ...EMPTY_PROBABILITIES };
  if (Array.isArray(value)) {
    value.slice(0, labels.length).forEach((score, index) => {
      result[labels[index]] = normalizeScore(score);
    });
    return result;
  }
  if (!isRecord(value)) return result;
  Object.entries(value).forEach(([label, score]) => {
    result[normalizeEmotion(label)] = normalizeScore(score);
  });
  return result;
}

function parseTranscript(value: unknown): TranscriptPayload {
  if (typeof value === 'string') {
    return { text: value, language: null, segments: [], available: value.length > 0, detail: null };
  }
  if (!isRecord(value)) {
    return { text: '', language: null, segments: [], available: false, detail: null };
  }
  const segments = Array.isArray(value.segments) ? value.segments.filter(isRecord) : [];
  return {
    text: asString(value.text ?? value.transcript),
    language: asString(value.language) || null,
    segments,
    available: value.available === undefined ? Boolean(value.text) : asBoolean(value.available),
    detail: asString(value.detail) || null,
  };
}

function parseTimelineItem(value: unknown, labels: EmotionKey[]): EmotionSegment | null {
  if (!isRecord(value)) return null;
  const start = asFiniteNumber(value.start ?? value.start_time ?? value.begin);
  const end = asFiniteNumber(value.end ?? value.end_time ?? value.stop, start);
  const rawLabel = value.label ?? value.emotion ?? value.prediction;
  const emotion = rawLabel === null || rawLabel === undefined ? null : normalizeEmotion(rawLabel);
  return {
    start,
    end: Math.max(start, end),
    emotion,
    confidence: value.confidence === undefined ? undefined : normalizeScore(value.confidence),
    probabilities: value.probabilities === undefined ? undefined : parseProbabilities(value.probabilities, labels),
    isSpeech: value.is_speech === undefined ? undefined : asBoolean(value.is_speech),
    text: asString(value.text) || undefined,
  };
}

function parseTimeline(value: unknown, labels: EmotionKey[]): EmotionSegment[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => parseTimelineItem(item, labels)).filter((item): item is EmotionSegment => Boolean(item));
}

function parseWaveform(value: unknown): WaveformPayload | undefined {
  if (!isRecord(value)) return undefined;
  const min = asNumberArray(value.min) ?? [];
  const max = asNumberArray(value.max) ?? [];
  const values = asNumberArray(value.values);
  if (min.length === 0 && max.length === 0 && !values) return undefined;
  return {
    ...value,
    sample_rate: asFiniteNumber(value.sample_rate),
    min,
    max,
    values,
    times: asNumberArray(value.times),
  };
}

function parseMel(value: unknown): MelPayload | undefined {
  if (!isRecord(value)) return undefined;
  const values = asMatrix(value.values);
  if (!values) return undefined;
  return {
    ...value,
    values,
    sample_rate: value.sample_rate === undefined ? undefined : asFiniteNumber(value.sample_rate),
    hop_length: value.hop_length === undefined ? undefined : asFiniteNumber(value.hop_length),
    n_mels: value.n_mels === undefined ? undefined : asFiniteNumber(value.n_mels),
  };
}

function findValue(root: UnknownRecord, keys: string[]): unknown {
  for (const key of keys) {
    if (root[key] !== undefined) return root[key];
  }
  for (const value of Object.values(root)) {
    if (!isRecord(value)) continue;
    const nested = findValue(value, keys);
    if (nested !== undefined) return nested;
  }
  return undefined;
}

function parseComparison(value: unknown): ModelComparisonRow[] {
  if (Array.isArray(value)) {
    return value.filter(isRecord).map((row, index) => ({
      model: asString(row.model ?? row.name, index === 0 ? 'CNN' : `模型 ${index + 1}`),
      uar: normalizeScore(row.uar ?? row.UAR),
      macroF1: normalizeScore(row.macroF1 ?? row.macro_f1 ?? row.f1),
      accuracy: normalizeScore(row.accuracy ?? row.acc),
      parameters: typeof row.parameters === 'string' || typeof row.parameters === 'number' ? row.parameters : undefined,
    }));
  }
  if (!isRecord(value)) return [];
  return Object.entries(value).filter(([, metrics]) => isRecord(metrics)).map(([model, metrics]) => {
    const row = metrics as UnknownRecord;
    return {
      model,
      uar: normalizeScore(row.uar ?? row.UAR),
      macroF1: normalizeScore(row.macroF1 ?? row.macro_f1 ?? row.f1),
      accuracy: normalizeScore(row.accuracy ?? row.acc),
      parameters: typeof row.parameters === 'string' || typeof row.parameters === 'number' ? row.parameters : undefined,
    };
  });
}

function parseFolds(value: unknown): FoldMetric[] {
  if (!Array.isArray(value)) return [];
  return value.filter(isRecord).map((row, index) => ({
    fold: asString(row.fold ?? row.name, `Fold ${index + 1}`),
    uar: normalizeScore(row.uar ?? row.UAR),
    macroF1: normalizeScore(row.macroF1 ?? row.macro_f1 ?? row.f1),
    accuracy: normalizeScore(row.accuracy ?? row.acc),
    trainSamples: row.trainSamples === undefined && row.train_samples === undefined ? undefined : asFiniteNumber(row.trainSamples ?? row.train_samples),
    testSamples: row.testSamples === undefined && row.test_samples === undefined ? undefined : asFiniteNumber(row.testSamples ?? row.test_samples),
  }));
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, { ...init, headers: { Accept: 'application/json', ...init?.headers } });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json() as UnknownRecord;
      detail = asString(body.detail ?? body.message, detail);
    } catch {
      // Keep the HTTP status when the response has no JSON body.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const payload = unwrap(await requestJson<unknown>('/health', { signal }));
  return {
    status: asString(payload.status) || undefined,
    model_ready: asBoolean(payload.model_ready),
    asr_ready: asBoolean(payload.asr_ready),
    model: asString(payload.model) || undefined,
    version: asString(payload.version) || undefined,
    detail: asString(payload.detail) || undefined,
  };
}

export async function predictAudio(file: Blob, filename: string, signal?: AbortSignal): Promise<PredictionResult> {
  const body = new FormData();
  body.append('file', file, filename);
  const payload = unwrap(await requestJson<unknown>('/predict', { method: 'POST', body, signal }));
  const labels = parseLabels(payload.labels);
  const audio = isRecord(payload.audio) ? payload.audio : {};
  const prediction = isRecord(payload.prediction) ? payload.prediction : {};
  return {
    labels,
    audio: {
      duration: asFiniteNumber(audio.duration),
      sampleRate: asFiniteNumber(audio.sample_rate),
      isSpeech: asBoolean(audio.is_speech),
    },
    prediction: {
      emotion: prediction.label === null || prediction.label === undefined ? null : normalizeEmotion(prediction.label),
      confidence: normalizeScore(prediction.confidence),
      probabilities: parseProbabilities(prediction.probabilities, labels),
    },
    transcript: parseTranscript(payload.transcript),
    timeline: parseTimeline(payload.timeline, labels),
    waveform: parseWaveform(payload.waveform),
    mel: parseMel(payload.mel),
  };
}

export async function getMetrics(signal?: AbortSignal): Promise<MetricsResponse> {
  const payload = unwrap(await requestJson<unknown>('/metrics', { signal }));
  const labels = parseLabels(payload.labels);
  const training = isRecord(payload.metrics) ? payload.metrics : payload;
  const models = isRecord(training.models) ? training.models : undefined;
  const primaryName = asString(training.primary, 'cnn');
  const primaryReport = models && isRecord(models[primaryName])
    ? models[primaryName] as UnknownRecord
    : models && isRecord(models.cnn)
      ? models.cnn as UnknownRecord
      : training;
  const outOfFold = isRecord(primaryReport.out_of_fold) ? primaryReport.out_of_fold : primaryReport;

  const compositeComparison = models
    ? Object.entries(models).filter((entry): entry is [string, UnknownRecord] => isRecord(entry[1])).map(([model, report]) => {
      const metrics = isRecord(report.out_of_fold) ? report.out_of_fold : report;
      return {
        model: model.toUpperCase(),
        uar: normalizeScore(metrics.uar ?? metrics.UAR),
        macroF1: normalizeScore(metrics.macro_f1 ?? metrics.macroF1 ?? metrics.f1),
        accuracy: normalizeScore(metrics.accuracy ?? metrics.acc),
      };
    })
    : [];
  const compositeFolds = Array.isArray(primaryReport.per_fold)
    ? primaryReport.per_fold.filter(isRecord).map((fold, index) => {
      const test = isRecord(fold.test) ? fold.test : {};
      const sizes = isRecord(fold.sizes) ? fold.sizes : {};
      return {
        fold: `Fold ${asFiniteNumber(fold.fold, index) + 1}`,
        uar: normalizeScore(test.uar ?? test.UAR),
        macroF1: normalizeScore(test.macro_f1 ?? test.macroF1 ?? test.f1),
        accuracy: normalizeScore(test.accuracy ?? test.acc),
        trainSamples: sizes.train === undefined ? undefined : asFiniteNumber(sizes.train),
        testSamples: sizes.test === undefined ? undefined : asFiniteNumber(sizes.test),
      };
    })
    : [];

  const comparisonValue = findValue(training, ['comparison', 'model_comparison', 'baselines']);
  const foldsValue = findValue(training, ['folds', 'fold_metrics', 'cross_validation', 'cv_folds']);
  const matrixValue = outOfFold.confusion_matrix ?? outOfFold.confusionMatrix ?? findValue(training, ['confusion_matrix', 'confusionMatrix', 'confusion']);
  const datasetValue = findValue(training, ['dataset', 'dataset_name', 'corpus']);
  const sampleCountValue = outOfFold.samples ?? findValue(training, ['sampleCount', 'sample_count', 'n_samples', 'num_samples', 'samples']);
  return {
    uar: normalizeScore(outOfFold.uar ?? outOfFold.UAR),
    macroF1: normalizeScore(outOfFold.macro_f1 ?? outOfFold.macroF1 ?? outOfFold.f1),
    accuracy: normalizeScore(outOfFold.accuracy ?? outOfFold.acc),
    comparison: compositeComparison.length > 0 ? compositeComparison : parseComparison(comparisonValue),
    confusionMatrix: asMatrix(matrixValue) ?? [],
    labels,
    folds: compositeFolds.length > 0 ? compositeFolds : parseFolds(foldsValue),
    dataset: asString(datasetValue) || undefined,
    sampleCount: sampleCountValue === undefined ? undefined : asFiniteNumber(sampleCountValue),
  };
}

export function parseStreamMessage(raw: string): StreamMessage {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error('服务端返回了无法解析的实时消息');
  }
  const payload = unwrap(parsed);
  if (payload.type === 'error') {
    return { type: 'error', error: asString(payload.error ?? payload.detail, '实时推理发生错误') };
  }
  const prediction = isRecord(payload.prediction) ? payload.prediction : {};
  const labels = parseLabels(payload.labels);
  const timeline = parseTimeline(payload.timeline, labels);
  return {
    type: asString(payload.type) || undefined,
    window: isRecord(payload.window) ? payload.window : undefined,
    emotion: prediction.label === null || prediction.label === undefined ? null : normalizeEmotion(prediction.label),
    confidence: prediction.confidence === undefined ? undefined : normalizeScore(prediction.confidence),
    probabilities: prediction.probabilities === undefined ? undefined : parseProbabilities(prediction.probabilities, labels),
    transcript: parseTranscript(payload.transcript),
    timeline,
  };
}

export function createStreamUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}${API_PREFIX}/ws/stream`;
}
