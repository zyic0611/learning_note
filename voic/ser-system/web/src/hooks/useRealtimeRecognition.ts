import { useCallback, useEffect, useRef, useState } from 'react';
import { createStreamUrl, parseStreamMessage } from '../api/client';
import { EMPTY_PROBABILITIES } from '../constants/emotions';
import type { EmotionKey, EmotionProbabilities, EmotionSegment, StreamMessage } from '../types/api';
import { StreamingPcm16Resampler } from '../utils/audio';

export type RealtimeStatus = 'idle' | 'requesting' | 'connecting' | 'streaming' | 'reconnecting' | 'error';

interface RuntimeResources {
  stream: MediaStream | null;
  context: AudioContext | null;
  source: MediaStreamAudioSourceNode | null;
  analyser: AnalyserNode | null;
  processor: ScriptProcessorNode | null;
  mute: GainNode | null;
  socket: WebSocket | null;
  resampler: StreamingPcm16Resampler | null;
}

const emptyResources = (): RuntimeResources => ({
  stream: null,
  context: null,
  source: null,
  analyser: null,
  processor: null,
  mute: null,
  socket: null,
  resampler: null,
});

function toReadableError(error: unknown): string {
  if (error instanceof DOMException) {
    if (error.name === 'NotAllowedError') return '麦克风权限被拒绝，请在浏览器设置中允许访问。';
    if (error.name === 'NotFoundError') return '未检测到可用麦克风。';
    if (error.name === 'NotReadableError') return '麦克风正被其他应用占用。';
  }
  return error instanceof Error ? error.message : '无法启动实时识别。';
}

export function useRealtimeRecognition() {
  const [status, setStatus] = useState<RealtimeStatus>('idle');
  const [error, setError] = useState('');
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null);
  const [emotion, setEmotion] = useState<EmotionKey | null>(null);
  const [probabilities, setProbabilities] = useState<EmotionProbabilities>({ ...EMPTY_PROBABILITIES });
  const [segments, setSegments] = useState<EmotionSegment[]>([]);
  const [finalTranscript, setFinalTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [elapsed, setElapsed] = useState(0);
  const resources = useRef<RuntimeResources>(emptyResources());
  const shouldRun = useRef(false);
  const sessionId = useRef(0);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<number | null>(null);
  const elapsedTimer = useRef<number | null>(null);
  const startedAt = useRef(0);

  const clearTimers = useCallback(() => {
    if (reconnectTimer.current !== null) window.clearTimeout(reconnectTimer.current);
    if (elapsedTimer.current !== null) window.clearInterval(elapsedTimer.current);
    reconnectTimer.current = null;
    elapsedTimer.current = null;
  }, []);

  const disconnectSocket = useCallback(() => {
    const socket = resources.current.socket;
    resources.current.socket = null;
    if (socket) {
      socket.onopen = null;
      socket.onmessage = null;
      socket.onerror = null;
      socket.onclose = null;
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) socket.close(1000, 'client-stop');
    }
  }, []);

  const releaseAudio = useCallback(async () => {
    const current = resources.current;
    if (current.processor) current.processor.onaudioprocess = null;
    current.source?.disconnect();
    current.analyser?.disconnect();
    current.processor?.disconnect();
    current.mute?.disconnect();
    current.stream?.getTracks().forEach((track) => track.stop());
    current.resampler?.reset();
    if (current.context && current.context.state !== 'closed') {
      try { await current.context.close(); } catch { /* Already closing. */ }
    }
    resources.current = emptyResources();
    setAnalyser(null);
  }, []);

  const resetResults = useCallback(() => {
    setEmotion(null);
    setProbabilities({ ...EMPTY_PROBABILITIES });
    setSegments([]);
    setFinalTranscript('');
    setInterimTranscript('');
    setElapsed(0);
  }, []);

  const consumeMessage = useCallback((message: StreamMessage) => {
    if (message.error) {
      setError(message.error);
      return;
    }
    if (message.emotion) setEmotion(message.emotion);
    if (message.probabilities) setProbabilities(message.probabilities);
    if (message.transcript) {
      setFinalTranscript(message.transcript.available ? message.transcript.text : '');
      setInterimTranscript(message.transcript.available ? '' : message.transcript.text);
    }
    if (message.timeline && message.timeline.length > 0) {
      setSegments(message.timeline.slice(-80));
    }
  }, []);

  const connectSocketRef = useRef<(id: number, reconnect?: boolean) => void>(() => undefined);
  connectSocketRef.current = (id, reconnect = false) => {
    if (!shouldRun.current || id !== sessionId.current) return;
    disconnectSocket();
    setStatus(reconnect ? 'reconnecting' : 'connecting');
    const socket = new WebSocket(createStreamUrl());
    socket.binaryType = 'arraybuffer';
    resources.current.socket = socket;

    socket.onopen = () => {
      if (!shouldRun.current || id !== sessionId.current) {
        socket.close();
        return;
      }
      socket.send(JSON.stringify({
        type: 'config',
        sample_rate: 16_000,
        channels: 1,
        format: 'pcm_s16le',
        language: null,
        transcribe: true,
      }));
      reconnectAttempts.current = 0;
      setStatus('streaming');
      setError('');
    };

    socket.onmessage = async (event) => {
      try {
        const raw = typeof event.data === 'string' ? event.data : event.data instanceof Blob ? await event.data.text() : new TextDecoder().decode(event.data);
        consumeMessage(parseStreamMessage(raw));
      } catch (messageError) {
        setError(toReadableError(messageError));
      }
    };

    socket.onerror = () => {
      if (shouldRun.current) setError('实时连接出现异常，正在尝试恢复。');
    };

    socket.onclose = (event) => {
      if (!shouldRun.current || id !== sessionId.current) return;
      const attempt = reconnectAttempts.current + 1;
      reconnectAttempts.current = attempt;
      if (attempt > 5) {
        shouldRun.current = false;
        clearTimers();
        disconnectSocket();
        void releaseAudio();
        setStatus('error');
        setError(`实时连接已中断（${event.code}），请重新开始。`);
        return;
      }
      setStatus('reconnecting');
      const delay = Math.min(8000, 600 * 2 ** (attempt - 1));
      reconnectTimer.current = window.setTimeout(() => connectSocketRef.current(id, true), delay);
    };
  };

  const stop = useCallback(async () => {
    shouldRun.current = false;
    sessionId.current += 1;
    clearTimers();
    disconnectSocket();
    await releaseAudio();
    setStatus('idle');
  }, [clearTimers, disconnectSocket, releaseAudio]);

  const start = useCallback(async () => {
    if (shouldRun.current) return;
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus('error');
      setError('当前浏览器不支持麦克风采集。');
      return;
    }

    const id = sessionId.current + 1;
    sessionId.current = id;
    shouldRun.current = true;
    reconnectAttempts.current = 0;
    setStatus('requesting');
    setError('');
    resetResults();

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      if (!shouldRun.current || id !== sessionId.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }

      const context = new AudioContext({ latencyHint: 'interactive' });
      await context.resume();
      const source = context.createMediaStreamSource(stream);
      const analyserNode = context.createAnalyser();
      analyserNode.fftSize = 2048;
      analyserNode.smoothingTimeConstant = 0.72;
      const processor = context.createScriptProcessor(4096, source.channelCount || 1, 1);
      const mute = context.createGain();
      mute.gain.value = 0;
      const resampler = new StreamingPcm16Resampler(context.sampleRate, 16_000);

      source.connect(analyserNode);
      analyserNode.connect(processor);
      processor.connect(mute);
      mute.connect(context.destination);
      resources.current = { stream, context, source, analyser: analyserNode, processor, mute, socket: null, resampler };
      setAnalyser(analyserNode);

      processor.onaudioprocess = (event) => {
        const channelCount = event.inputBuffer.numberOfChannels;
        const mono = new Float32Array(event.inputBuffer.length);
        for (let channel = 0; channel < channelCount; channel += 1) {
          const samples = event.inputBuffer.getChannelData(channel);
          for (let index = 0; index < samples.length; index += 1) mono[index] += samples[index] / channelCount;
        }
        const chunk = resampler.push(mono);
        const socket = resources.current.socket;
        if (chunk.byteLength > 0 && socket?.readyState === WebSocket.OPEN) socket.send(chunk);
      };

      startedAt.current = performance.now();
      elapsedTimer.current = window.setInterval(() => setElapsed((performance.now() - startedAt.current) / 1000), 250);
      connectSocketRef.current(id);
    } catch (startError) {
      shouldRun.current = false;
      setStatus('error');
      setError(toReadableError(startError));
      await releaseAudio();
    }
  }, [releaseAudio, resetResults]);

  useEffect(() => () => {
    shouldRun.current = false;
    sessionId.current += 1;
    clearTimers();
    disconnectSocket();
    void releaseAudio();
  }, [clearTimers, disconnectSocket, releaseAudio]);

  return {
    status,
    error,
    analyser,
    emotion,
    probabilities,
    segments,
    transcript: finalTranscript,
    interimTranscript,
    elapsed,
    start,
    stop,
    isActive: status !== 'idle' && status !== 'error',
  };
}
