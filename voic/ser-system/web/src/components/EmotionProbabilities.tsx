import { EMOTIONS, formatPercent } from '../constants/emotions';
import type { EmotionKey, EmotionProbabilities as EmotionScores } from '../types/api';

interface EmotionProbabilitiesProps {
  probabilities: EmotionScores;
  activeEmotion?: EmotionKey;
  compact?: boolean;
}

export default function EmotionProbabilities({ probabilities, activeEmotion, compact = false }: EmotionProbabilitiesProps) {
  return (
    <div className={`probability-list ${compact ? 'probability-list-compact' : ''}`} role="list" aria-label="情感概率分布">
      {EMOTIONS.map((emotion) => {
        const value = Math.max(0, Math.min(1, probabilities[emotion.key] ?? 0));
        const isActive = activeEmotion === emotion.key;
        return (
          <div className={`probability-row ${isActive ? 'is-active' : ''}`} key={emotion.key} role="listitem">
            <div className="probability-label">
              <span className="emotion-key" style={{ backgroundColor: emotion.color }} aria-hidden="true" />
              <span>{emotion.label}</span>
            </div>
            <div className="probability-track" aria-hidden="true">
              <span style={{ width: `${value * 100}%`, backgroundColor: emotion.color }} />
            </div>
            <span className="probability-value">{formatPercent(value)}</span>
          </div>
        );
      })}
    </div>
  );
}
