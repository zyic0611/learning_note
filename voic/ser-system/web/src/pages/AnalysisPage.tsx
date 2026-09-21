import { useCallback, useEffect, useRef, useState } from 'react';
import { Alert, Button, Progress, Tag } from 'antd';
import { CircleStop, FileAudio2, Mic, Sparkles, UploadCloud, X } from 'lucide-react';
import { predictAudio } from '../api/client';
import EmotionProbabilities from '../components/EmotionProbabilities';
import EmotionTimeline from '../components/EmotionTimeline';
import MelSpectrogram from '../components/MelSpectrogram';
import PageHeader from '../components/PageHeader';
import SectionCard from '../components/SectionCard';
import StatePanel from '../components/StatePanel';
import WaveformCanvas from '../components/WaveformCanvas';
import { EMOTION_MAP, formatPercent } from '../constants/emotions';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import type { PredictionResult } from '../types/api';
import { formatDuration, readAudioWaveform } from '../utils/audio';

interface AudioSelection {
  blob: Blob;
  filename: string;
  url: string;
  size: number;
  waveform?: number[];
  duration?: number;
}

const MAX_FILE_SIZE = 25 * 1024 * 1024;
const ACCEPTED_EXTENSIONS = /\.(wav|mp3|m4a|webm)$/i;

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function AnalysisPage() {
  const [selection, setSelection] = useState<AudioSelection | null>(null);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [phase, setPhase] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [error, setError] = useState('');
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const requestRef = useRef<AbortController | null>(null);
  const selectionRef = useRef<AudioSelection | null>(null);

  useEffect(() => { selectionRef.current = selection; }, [selection]);

  const selectBlob = useCallback((blob: Blob, filename: string) => {
    if (blob.size > MAX_FILE_SIZE) {
      setError('文件超过 25 MB，请选择更短的音频。');
      setPhase('error');
      return;
    }
    if (!ACCEPTED_EXTENSIONS.test(filename)) {
      setError('不支持该文件格式，请选择 WAV、MP3、M4A 或 WebM。');
      setPhase('error');
      return;
    }
    requestRef.current?.abort();
    setSelection((current) => {
      if (current) URL.revokeObjectURL(current.url);
      return { blob, filename, url: URL.createObjectURL(blob), size: blob.size };
    });
    setResult(null);
    setError('');
    setPhase('idle');
    void readAudioWaveform(blob).then(({ waveform, duration }) => {
      setSelection((current) => current?.blob === blob ? { ...current, waveform, duration } : current);
    }).catch(() => undefined);
  }, []);

  const recorder = useAudioRecorder(selectBlob);

  const clearSelection = useCallback(() => {
    requestRef.current?.abort();
    requestRef.current = null;
    setSelection((current) => {
      if (current) URL.revokeObjectURL(current.url);
      return null;
    });
    setResult(null);
    setError('');
    setPhase('idle');
    if (inputRef.current) inputRef.current.value = '';
  }, []);

  useEffect(() => () => {
    requestRef.current?.abort();
    if (selectionRef.current) URL.revokeObjectURL(selectionRef.current.url);
  }, []);

  const analyze = useCallback(async () => {
    if (!selection) return;
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    setPhase('loading');
    setError('');
    setResult(null);
    try {
      const response = await predictAudio(selection.blob, selection.filename, controller.signal);
      setResult(response);
      setPhase('success');
    } catch (requestError) {
      if (requestError instanceof DOMException && requestError.name === 'AbortError') return;
      setError(requestError instanceof Error ? requestError.message : '分析请求失败，请稍后重试。');
      setPhase('error');
    }
  }, [selection]);

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0];
    if (file) selectBlob(file, file.name);
  };

  const dominant = result?.prediction.emotion ? EMOTION_MAP[result.prediction.emotion] : null;
  const confidence = result?.prediction.confidence ?? 0;
  const apiWaveform = result?.waveform?.values
    ?? (result?.waveform?.max.length ? result.waveform.max.flatMap((maximum, index) => [maximum, result.waveform?.min[index] ?? -maximum]) : undefined);
  const visualWaveform = apiWaveform ?? selection?.waveform;
  const displayDuration = result?.audio.duration || selection?.duration;

  return (
    <main className="page-stack analysis-page">
      <PageHeader
        eyebrow="Offline Inference"
        title="音频文件分析"
        description="上传已有音频或直接在浏览器录制，一次性获取整段情感、转写与分段结果。"
        actions={<Tag className="format-tag">WAV · MP3 · M4A · WEBM</Tag>}
      />

      {(error || recorder.error) && <Alert type="error" showIcon message={error || recorder.error} closable />}

      <div className="analysis-source-grid">
        <SectionCard title="选择音频" subtitle="拖放文件或从本机选择，最大 25 MB">
          <div
            className={`drop-zone ${dragging ? 'is-dragging' : ''} ${selection ? 'has-file' : ''}`}
            onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => { event.preventDefault(); setDragging(false); handleFiles(event.dataTransfer.files); }}
            onClick={() => !selection && inputRef.current?.click()}
            onKeyDown={(event) => { if (!selection && (event.key === 'Enter' || event.key === ' ')) inputRef.current?.click(); }}
            role="button"
            tabIndex={0}
          >
            <input ref={inputRef} type="file" accept=".wav,.mp3,.m4a,.webm,audio/wav,audio/mpeg,audio/mp4,audio/webm" hidden onChange={(event) => handleFiles(event.target.files)} />
            {selection ? (
              <div className="selected-file">
                <div className="file-icon"><FileAudio2 size={28} /></div>
                <div className="file-copy"><strong title={selection.filename}>{selection.filename}</strong><span>{formatBytes(selection.size)}{displayDuration ? ` · ${formatDuration(displayDuration)}` : ''}</span></div>
                <button type="button" className="icon-button" onClick={(event) => { event.stopPropagation(); clearSelection(); }} aria-label="移除音频"><X size={18} /></button>
              </div>
            ) : (
              <div className="drop-copy">
                <UploadCloud size={34} />
                <strong>将音频拖放到这里</strong>
                <span>或点击浏览本机文件</span>
              </div>
            )}
          </div>
        </SectionCard>

        <SectionCard title="现场录音" subtitle="使用当前设备麦克风创建待分析音频">
          <div className={`record-panel ${recorder.state === 'recording' ? 'is-recording' : ''}`}>
            <button
              type="button"
              className="record-button"
              onClick={() => recorder.state === 'recording' ? recorder.stop() : void recorder.start()}
              disabled={recorder.state === 'requesting'}
              aria-label={recorder.state === 'recording' ? '停止录音' : '开始录音'}
            >
              {recorder.state === 'recording' ? <CircleStop size={29} /> : <Mic size={29} />}
            </button>
            <div><strong>{recorder.state === 'recording' ? '正在录音' : recorder.state === 'requesting' ? '等待授权' : '录制一段新音频'}</strong><span>{recorder.state === 'recording' ? formatDuration(recorder.elapsed) : '录制完成后自动载入'}</span></div>
            {recorder.state === 'recording' && <div className="record-level"><i /><i /><i /><i /><i /></div>}
          </div>
        </SectionCard>
      </div>

      {selection && (
        <SectionCard title="音频预览" subtitle="确认内容后提交至离线推理接口" extra={<span className="sample-rate-note">原始采样率由服务端统一处理</span>}>
          <div className="audio-preview">
            <audio controls src={selection.url} preload="metadata">当前浏览器不支持音频播放。</audio>
            <div className="preview-waveform"><WaveformCanvas data={visualWaveform} active={false} label="待分析音频波形" /></div>
            <Button type="primary" size="large" icon={phase === 'loading' ? undefined : <Sparkles size={17} />} loading={phase === 'loading'} onClick={() => void analyze()}>
              {phase === 'loading' ? '模型分析中' : result ? '重新分析' : '开始分析'}
            </Button>
          </div>
          {phase === 'loading' && <Progress percent={68} showInfo={false} status="active" strokeColor="#20b8a6" trailColor="rgba(111,143,166,.14)" />}
        </SectionCard>
      )}

      {!selection && phase === 'idle' && (
        <StatePanel kind="empty" title="尚未选择音频" description="上传文件或完成一次现场录音后，将在这里展示模型结果。" />
      )}
      {phase === 'error' && selection && (
        <StatePanel kind="error" title="分析失败" description={error || '服务暂时不可用，请稍后重试。'} onRetry={() => void analyze()} />
      )}
      {phase === 'loading' && <StatePanel kind="loading" title="正在提取声学特征" description="模型正在计算 Mel 频谱、情感分布与语音转写。" />}

      {result && phase === 'success' && dominant && (
        <div className="result-stack">
          <div className="analysis-result-grid">
            <SectionCard title="整体识别结果" subtitle="整段音频的主导情感">
              <div className="analysis-emotion-summary">
                <div className="result-emotion-mark" style={{ backgroundColor: dominant.softColor, color: dominant.color }}><Sparkles size={27} /></div>
                <div><span>识别为</span><strong>{dominant.label}</strong><p>{dominant.description}</p></div>
                <div className="result-confidence"><span>置信度</span><b>{formatPercent(confidence)}</b></div>
              </div>
              <EmotionProbabilities probabilities={result.prediction.probabilities} activeEmotion={result.prediction.emotion ?? undefined} />
            </SectionCard>
            <SectionCard title="语音转写" subtitle="由语音识别模块返回的文本">
              <div className="analysis-transcript">
                {result.transcript.available && result.transcript.text ? <p>{result.transcript.text}</p> : <span>{result.transcript.detail ?? '接口未返回转写文本'}</span>}
              </div>
              <div className="transcript-meta"><span>时长 {displayDuration ? formatDuration(displayDuration) : '—'}</span><span>分段 {result.timeline.length}</span>{result.audio.sampleRate > 0 && <span>{result.audio.sampleRate.toLocaleString()} Hz</span>}{result.transcript.language && <span>{result.transcript.language}</span>}</div>
            </SectionCard>
          </div>

          {result.mel?.values && result.mel.values.length > 0 && (
            <SectionCard title="Mel 频谱图" subtitle="对数 Mel 能量随时间的分布；颜色越亮表示能量越高">
              <MelSpectrogram data={result.mel.values} duration={displayDuration} />
            </SectionCard>
          )}

          <SectionCard title="分段情感时间线" subtitle="模型对局部语音片段的情感判断">
            <EmotionTimeline segments={result.timeline} duration={displayDuration} emptyText="接口未返回分段结果" />
          </SectionCard>
        </div>
      )}
    </main>
  );
}
