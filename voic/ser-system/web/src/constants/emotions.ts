import type { EmotionKey, EmotionProbabilities } from '../types/api';

export interface EmotionMeta {
  key: EmotionKey;
  label: string;
  color: string;
  softColor: string;
  description: string;
}

export const EMOTIONS: EmotionMeta[] = [
  { key: 'neutral', label: '中性', color: '#3987e5', softColor: 'rgba(57, 135, 229, 0.16)', description: '语调平稳' },
  { key: 'happy', label: '高兴', color: '#d95926', softColor: 'rgba(217, 89, 38, 0.16)', description: '积极愉悦' },
  { key: 'sad', label: '悲伤', color: '#199e70', softColor: 'rgba(25, 158, 112, 0.16)', description: '低沉消极' },
  { key: 'angry', label: '愤怒', color: '#c98500', softColor: 'rgba(201, 133, 0, 0.16)', description: '激动强烈' },
  { key: 'fear', label: '恐惧', color: '#d55181', softColor: 'rgba(213, 81, 129, 0.16)', description: '紧张不安' },
  { key: 'disgust', label: '厌恶', color: '#008300', softColor: 'rgba(0, 131, 0, 0.16)', description: '排斥反感' },
];

export const EMOTION_MAP = Object.fromEntries(EMOTIONS.map((item) => [item.key, item])) as Record<EmotionKey, EmotionMeta>;

export const EMPTY_PROBABILITIES: EmotionProbabilities = {
  neutral: 0,
  happy: 0,
  sad: 0,
  angry: 0,
  fear: 0,
  disgust: 0,
};

const ALIASES: Record<string, EmotionKey> = {
  neutral: 'neutral',
  neutrality: 'neutral',
  中性: 'neutral',
  平静: 'neutral',
  happy: 'happy',
  happiness: 'happy',
  joy: 'happy',
  高兴: 'happy',
  开心: 'happy',
  sad: 'sad',
  sadness: 'sad',
  悲伤: 'sad',
  难过: 'sad',
  angry: 'angry',
  anger: 'angry',
  愤怒: 'angry',
  fear: 'fear',
  fearful: 'fear',
  恐惧: 'fear',
  disgust: 'disgust',
  disgusted: 'disgust',
  厌恶: 'disgust',
  反感: 'disgust',
};

export function normalizeEmotion(value: unknown): EmotionKey {
  if (typeof value !== 'string') return 'neutral';
  return ALIASES[value.trim().toLowerCase()] ?? ALIASES[value.trim()] ?? 'neutral';
}

export function formatPercent(value: number, digits = 1): string {
  const normalized = value > 1 ? value / 100 : value;
  return `${(Math.max(0, normalized) * 100).toFixed(digits)}%`;
}
