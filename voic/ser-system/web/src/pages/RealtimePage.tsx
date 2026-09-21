import type { CSSProperties } from 'react';
import { Alert, Button, Tag } from 'antd';
import { AudioLines, CircleStop, Mic, Radio, RotateCcw, Wifi, WifiOff } from 'lucide-react';
import EmotionProbabilities from '../components/EmotionProbabilities';
import EmotionTimeline from '../components/EmotionTimeline';
import PageHeader from '../components/PageHeader';
import SectionCard from '../components/SectionCard';
import WaveformCanvas from '../components/WaveformCanvas';
import { EMOTION_MAP, formatPercent } from '../constants/emotions';
import { useRealtimeRecognition, type RealtimeStatus } from '../hooks/useRealtimeRecognition';
import { formatDuration } from '../utils/audio';

const STATUS_COPY: Record<RealtimeStatus, string> = {
  idle: '就绪',
  requesting: '等待麦克风授权',
  connecting: '正在连接',
  streaming: '实时识别中',
  reconnecting: '正在重连',
  error: '连接异常',
};

export default function RealtimePage() {
  const realtime = useRealtimeRecognition();
  const activeMeta = realtime.emotion ? EMOTION_MAP[realtime.emotion] : null;
  const confidence = realtime.emotion ? realtime.probabilities[realtime.emotion] : 0;
  const isConnecting = realtime.status === 'requesting' || realtime.status === 'connecting';

  return (
    <main className="page-stack realtime-page">
      <PageHeader
        eyebrow="Live Inference"
        title="实时语音情感识别"
        description="采集麦克风音频并以 16 kHz 单声道 PCM16 流式推理，观察语义与情感随时间的变化。"
        actions={
          <div className={`connection-state connection-${realtime.status}`}>
            {realtime.status === 'streaming' ? <Wifi size={15} /> : realtime.status === 'error' ? <WifiOff size={15} /> : <Radio size={15} />}
            {STATUS_COPY[realtime.status]}
          </div>
        }
      />

      {realtime.error && (
        <Alert type={realtime.status === 'error' ? 'error' : 'warning'} showIcon message={realtime.error} closable />
      )}

      <div className="realtime-hero-grid">
        <SectionCard className="capture-card">
          <div className="capture-panel">
            <div className={`mic-stage ${realtime.isActive ? 'is-recording' : ''}`}>
              <span className="mic-ring mic-ring-one" />
              <span className="mic-ring mic-ring-two" />
              <button
                type="button"
                className="mic-button"
                onClick={() => realtime.isActive ? void realtime.stop() : void realtime.start()}
                disabled={isConnecting}
                aria-label={realtime.isActive ? '停止实时识别' : '开始实时识别'}
              >
                {realtime.isActive ? <CircleStop size={35} /> : <Mic size={38} />}
              </button>
            </div>
            <h2>{realtime.isActive ? '正在聆听' : realtime.status === 'error' ? '识别未启动' : '开始一次实时识别'}</h2>
            <p>{realtime.isActive ? '请以自然语速说话，结果将持续更新' : '点击麦克风并允许浏览器访问音频设备'}</p>
            <div className="capture-meta">
              <span><i className={realtime.isActive ? 'live-dot' : ''} />{formatDuration(realtime.elapsed)}</span>
              <span>16,000 Hz</span>
              <span>PCM · 16 bit</span>
            </div>
            {realtime.status === 'error' && (
              <Button icon={<RotateCcw size={15} />} onClick={() => void realtime.start()}>重新尝试</Button>
            )}
          </div>
        </SectionCard>

        <SectionCard title="当前情感" subtitle="最新推理窗口的主导类别与置信度" className="current-emotion-card">
          <div className="emotion-hero">
            <div className="emotion-orbit" style={{ '--emotion-color': activeMeta?.color ?? '#6f879b' } as CSSProperties}>
              <AudioLines size={28} />
            </div>
            <div>
              <span className="emotion-kicker">Dominant emotion</span>
              <strong>{activeMeta?.label ?? '等待输入'}</strong>
              <p>{activeMeta ? activeMeta.description : '开始录音后显示实时结果'}</p>
            </div>
            <div className="confidence-figure">
              <span>置信度</span>
              <b>{activeMeta ? formatPercent(confidence) : '—'}</b>
            </div>
          </div>
          <EmotionProbabilities probabilities={realtime.probabilities} activeEmotion={realtime.emotion ?? undefined} compact />
        </SectionCard>
      </div>

      <SectionCard
        title="实时声学波形"
        subtitle="麦克风时域信号，仅在浏览器内用于可视化"
        extra={<Tag bordered={false} color={realtime.isActive ? 'cyan' : 'default'}>{realtime.isActive ? 'LIVE' : 'STANDBY'}</Tag>}
      >
        <div className="waveform-stage">
          <WaveformCanvas analyser={realtime.analyser} active={realtime.isActive} label="实时麦克风波形" />
          <div className="waveform-scale"><span>+1.0</span><span>0</span><span>−1.0</span></div>
        </div>
      </SectionCard>

      <div className="realtime-bottom-grid">
        <SectionCard title="情感时间线" subtitle="最近识别片段，悬停可查看时间与置信度">
          <EmotionTimeline segments={realtime.segments} duration={realtime.elapsed} scroll emptyText="开始说话后生成情感片段" />
        </SectionCard>
        <SectionCard title="增量转写" subtitle="最终文本与当前未定稿内容">
          <div className="transcript-panel" aria-live="polite">
            {realtime.transcript || realtime.interimTranscript ? (
              <p><span>{realtime.transcript}</span>{realtime.transcript && realtime.interimTranscript && ' '}<em>{realtime.interimTranscript}</em><i className="text-caret" /></p>
            ) : (
              <div className="transcript-empty"><AudioLines size={21} /><span>语音内容将在此逐步呈现</span></div>
            )}
          </div>
        </SectionCard>
      </div>
    </main>
  );
}
