import { EMOTION_MAP, EMOTIONS, formatPercent } from '../constants/emotions';
import type { EmotionSegment } from '../types/api';
import { formatTimePoint } from '../utils/format';

interface EmotionTimelineProps {
  segments: EmotionSegment[];
  duration?: number;
  emptyText?: string;
  scroll?: boolean;
}

export default function EmotionTimeline({ segments, duration, emptyText = '等待情感片段', scroll = false }: EmotionTimelineProps) {
  if (segments.length === 0) {
    return <div className="timeline-empty"><span className="empty-pulse" />{emptyText}</div>;
  }

  const maxEnd = Math.max(duration ?? 0, ...segments.map((segment) => segment.end), 1);

  return (
    <div>
      <div className="emotion-legend" aria-label="情感图例">
        {EMOTIONS.map((emotion) => (
          <span key={emotion.key}><i style={{ backgroundColor: emotion.color }} />{emotion.label}</span>
        ))}
      </div>
      <div className={`emotion-timeline ${scroll ? 'emotion-timeline-scroll' : ''}`}>
        <div className="timeline-track" style={{ minWidth: scroll ? `${Math.max(680, maxEnd * 42)}px` : undefined }}>
          {segments.map((segment, index) => {
            const meta = segment.emotion ? EMOTION_MAP[segment.emotion] : null;
            const label = meta?.label ?? (segment.isSpeech === false ? '非语音' : '未识别');
            const color = meta?.color ?? '#526d83';
            const left = (segment.start / maxEnd) * 100;
            const width = Math.max(0.7, ((Math.max(segment.end, segment.start + 0.05) - segment.start) / maxEnd) * 100);
            return (
              <button
                type="button"
                className="timeline-segment"
                key={`${segment.start}-${segment.end}-${index}`}
                style={{ left: `${left}%`, width: `${width}%`, backgroundColor: color }}
                title={`${formatTimePoint(segment.start)}–${formatTimePoint(segment.end)} · ${label}${segment.confidence === undefined ? '' : ` ${formatPercent(segment.confidence)}`}`}
                aria-label={`${formatTimePoint(segment.start)} 至 ${formatTimePoint(segment.end)}，${label}`}
              />
            );
          })}
          <div className="timeline-axis">
            <span>00:00.0</span>
            <span>{formatTimePoint(maxEnd / 2)}</span>
            <span>{formatTimePoint(maxEnd)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
