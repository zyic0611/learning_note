import { useCallback, useEffect, useRef, useState } from 'react';
import { getSupportedRecordingMimeType } from '../utils/audio';

export type RecorderState = 'idle' | 'requesting' | 'recording' | 'error';

function recorderError(error: unknown): string {
  if (error instanceof DOMException) {
    if (error.name === 'NotAllowedError') return '麦克风权限被拒绝，请允许访问后重试。';
    if (error.name === 'NotFoundError') return '未检测到可用麦克风。';
    if (error.name === 'NotReadableError') return '麦克风正被其他程序占用。';
  }
  return error instanceof Error ? error.message : '无法使用浏览器录音。';
}

export function useAudioRecorder(onComplete: (blob: Blob, filename: string) => void) {
  const [state, setState] = useState<RecorderState>('idle');
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState('');
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const startedAtRef = useRef(0);

  const release = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    recorderRef.current = null;
    if (timerRef.current !== null) window.clearInterval(timerRef.current);
    timerRef.current = null;
  }, []);

  const stop = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder?.state === 'recording') recorder.stop();
    else {
      release();
      setState('idle');
    }
  }, [release]);

  const start = useCallback(async () => {
    if (state === 'recording' || state === 'requesting') return;
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setState('error');
      setError('当前浏览器不支持网页录音。');
      return;
    }
    setState('requesting');
    setError('');
    setElapsed(0);
    chunksRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
      const mimeType = getSupportedRecordingMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      streamRef.current = stream;
      recorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onerror = () => {
        setError('录音过程中发生错误，请重新录制。');
        setState('error');
        release();
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        const extension = recorder.mimeType.includes('mp4') ? 'm4a' : 'webm';
        release();
        setState('idle');
        if (blob.size > 0) onComplete(blob, `recording-${new Date().toISOString().replace(/[:.]/g, '-')}.${extension}`);
      };
      recorder.start(500);
      startedAtRef.current = performance.now();
      timerRef.current = window.setInterval(() => setElapsed((performance.now() - startedAtRef.current) / 1000), 200);
      setState('recording');
    } catch (recordError) {
      release();
      setState('error');
      setError(recorderError(recordError));
    }
  }, [onComplete, release, state]);

  useEffect(() => () => {
    const recorder = recorderRef.current;
    recorderRef.current = null;
    if (recorder) {
      recorder.ondataavailable = null;
      recorder.onstop = null;
      if (recorder.state === 'recording') recorder.stop();
    }
    release();
  }, [release]);

  return { state, elapsed, error, start, stop };
}
