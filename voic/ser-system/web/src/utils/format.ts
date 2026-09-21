export function asFiniteNumber(value: unknown, fallback = 0): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const parsed = Number(value.replace('%', ''));
    if (Number.isFinite(parsed)) return value.includes('%') ? parsed / 100 : parsed;
  }
  return fallback;
}

export function normalizeScore(value: unknown): number {
  const score = asFiniteNumber(value);
  return Math.max(0, Math.min(1, score > 1 ? score / 100 : score));
}

export function formatMetric(value: number): string {
  return `${(normalizeScore(value) * 100).toFixed(1)}%`;
}

export function formatTimePoint(seconds: number): string {
  const safe = Math.max(0, seconds);
  const minutes = Math.floor(safe / 60);
  const remainder = safe - minutes * 60;
  return `${minutes.toString().padStart(2, '0')}:${remainder.toFixed(1).padStart(4, '0')}`;
}
