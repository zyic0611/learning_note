export const EMOTION_KEYS = ['neutral', 'happy', 'sad', 'angry', 'fear', 'disgust'] as const;

export type EmotionKey = (typeof EMOTION_KEYS)[number];
export type EmotionProbabilities = Record<EmotionKey, number>;
export type ApiProbabilities = Record<string, number> | number[];

export interface HealthResponse {
  status?: string;
  model_ready: boolean;
  asr_ready: boolean;
  model?: string;
  version?: string;
  detail?: string;
}

export interface AudioMetadata {
  duration: number;
  sample_rate: number;
  is_speech: boolean;
}

export interface PredictionPayload {
  label: string | null;
  confidence: number;
  probabilities: ApiProbabilities;
}

export interface TranscriptSegmentPayload {
  start?: number;
  end?: number;
  text?: string;
  [key: string]: unknown;
}

export interface TranscriptPayload {
  text: string;
  language: string | null;
  segments: TranscriptSegmentPayload[];
  available: boolean;
  detail: string | null;
}

export interface TimelinePayload {
  start: number;
  end: number;
  label: string | null;
  confidence: number;
  probabilities: ApiProbabilities;
  is_speech: boolean;
}

export interface WaveformPayload {
  sample_rate: number;
  min: number[];
  max: number[];
  values?: number[];
  times?: number[];
  [key: string]: unknown;
}

export interface MelPayload {
  values: number[][];
  sample_rate?: number;
  hop_length?: number;
  n_mels?: number;
  [key: string]: unknown;
}

export interface PredictApiResponse {
  labels: string[];
  audio: AudioMetadata;
  prediction: PredictionPayload;
  transcript: TranscriptPayload;
  timeline: TimelinePayload[];
  waveform: WaveformPayload;
  mel: MelPayload;
}

export interface StreamWindowPayload {
  start?: number;
  end?: number;
  duration?: number;
  [key: string]: unknown;
}

export interface StreamPredictionApiMessage {
  type: 'prediction';
  window: StreamWindowPayload;
  prediction: PredictionPayload;
  transcript: TranscriptPayload;
  timeline: TimelinePayload[];
}

export interface StreamErrorApiMessage {
  type: 'error';
  error?: string;
  detail?: string;
}

export type StreamApiMessage = StreamPredictionApiMessage | StreamErrorApiMessage;

export interface EmotionSegment {
  start: number;
  end: number;
  emotion: EmotionKey | null;
  confidence?: number;
  probabilities?: EmotionProbabilities;
  isSpeech?: boolean;
  text?: string;
}

export interface PredictionResult {
  labels: EmotionKey[];
  audio: {
    duration: number;
    sampleRate: number;
    isSpeech: boolean;
  };
  prediction: {
    emotion: EmotionKey | null;
    confidence: number;
    probabilities: EmotionProbabilities;
  };
  transcript: TranscriptPayload;
  timeline: EmotionSegment[];
  waveform?: WaveformPayload;
  mel?: MelPayload;
}

export interface StreamMessage {
  type?: string;
  window?: StreamWindowPayload;
  emotion?: EmotionKey | null;
  confidence?: number;
  probabilities?: EmotionProbabilities;
  transcript?: TranscriptPayload;
  timeline?: EmotionSegment[];
  error?: string;
}

export interface ModelComparisonRow {
  model: string;
  uar: number;
  macroF1: number;
  accuracy: number;
  parameters?: string | number;
}

export interface FoldMetric {
  fold: string;
  uar: number;
  macroF1: number;
  accuracy: number;
  trainSamples?: number;
  testSamples?: number;
}

export interface ClassificationMetricBlock {
  samples: number;
  accuracy: number;
  uar: number;
  macro_f1: number;
  confusion_matrix: number[][];
  per_class_precision: number[] | Record<string, number>;
  per_class_recall: number[] | Record<string, number>;
  per_class_f1: number[] | Record<string, number>;
  support: number[] | Record<string, number>;
  per_corpus?: Record<string, ClassificationMetricBlock>;
}

export interface TrainingFoldReport {
  fold: number;
  artifact: string;
  sizes: { train: number; val: number; test: number };
  epochs_completed?: number;
  best_epoch?: number;
  history?: Record<string, unknown>;
  val: ClassificationMetricBlock;
  test: ClassificationMetricBlock;
}

export interface ModelTrainingReport {
  model_type: 'cnn' | 'svm';
  seed: number;
  n_folds: number;
  folds_run: number[];
  cache: unknown;
  best_artifact: unknown;
  selection: unknown;
  per_fold: TrainingFoldReport[];
  out_of_fold: ClassificationMetricBlock;
}

export interface CompositeTrainingMetrics {
  labels: string[];
  models: Record<string, ModelTrainingReport> & {
    cnn?: ModelTrainingReport;
    svm?: ModelTrainingReport;
  };
  primary: string;
}

export interface MetricsApiResponse {
  labels: string[];
  metrics: CompositeTrainingMetrics | ModelTrainingReport;
}

export interface MetricsResponse {
  uar: number;
  macroF1: number;
  accuracy: number;
  comparison: ModelComparisonRow[];
  confusionMatrix: number[][];
  labels: EmotionKey[];
  folds: FoldMetric[];
  dataset?: string;
  sampleCount?: number;
}

export type UnknownRecord = Record<string, unknown>;
