import { useEffect, useRef } from 'react';

interface WaveformCanvasProps {
  analyser?: AnalyserNode | null;
  data?: number[];
  active?: boolean;
  label?: string;
}

export default function WaveformCanvas({ analyser, data, active = false, label = '音频波形' }: WaveformCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext('2d');
    if (!context) return;

    let frame = 0;
    const byteData = analyser ? new Uint8Array(analyser.fftSize) : null;

    const draw = () => {
      const ratio = window.devicePixelRatio || 1;
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      if (canvas.width !== Math.floor(width * ratio) || canvas.height !== Math.floor(height * ratio)) {
        canvas.width = Math.floor(width * ratio);
        canvas.height = Math.floor(height * ratio);
      }
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      context.clearRect(0, 0, width, height);

      const gradient = context.createLinearGradient(0, 0, 0, height);
      gradient.addColorStop(0, 'rgba(32, 184, 166, 0.22)');
      gradient.addColorStop(1, 'rgba(32, 184, 166, 0)');
      context.fillStyle = gradient;

      const source = (() => {
        if (analyser && byteData) {
          analyser.getByteTimeDomainData(byteData);
          return Array.from(byteData, (value) => (value - 128) / 128);
        }
        if (data && data.length > 0) return data;
        return Array.from({ length: 180 }, (_, index) => active ? Math.sin(index * 0.14) * 0.015 : 0);
      })();

      const step = width / Math.max(1, source.length - 1);
      const center = height / 2;
      const amplitude = Math.max(10, height * 0.38);
      context.beginPath();
      source.forEach((sample, index) => {
        const x = index * step;
        const y = center - Math.max(-1, Math.min(1, sample)) * amplitude;
        if (index === 0) context.moveTo(x, y);
        else context.lineTo(x, y);
      });
      context.lineTo(width, center);
      context.lineTo(0, center);
      context.closePath();
      context.fill();

      context.beginPath();
      context.strokeStyle = active || data?.length ? '#35c9b8' : 'rgba(126, 157, 180, 0.44)';
      context.lineWidth = 2;
      context.lineJoin = 'round';
      context.lineCap = 'round';
      source.forEach((sample, index) => {
        const x = index * step;
        const y = center - Math.max(-1, Math.min(1, sample)) * amplitude;
        if (index === 0) context.moveTo(x, y);
        else context.lineTo(x, y);
      });
      context.stroke();

      context.beginPath();
      context.strokeStyle = 'rgba(139, 170, 192, 0.16)';
      context.lineWidth = 1;
      context.moveTo(0, Math.round(center) + 0.5);
      context.lineTo(width, Math.round(center) + 0.5);
      context.stroke();

      if (analyser && active) frame = window.requestAnimationFrame(draw);
    };

    draw();
    return () => window.cancelAnimationFrame(frame);
  }, [active, analyser, data]);

  return <canvas ref={canvasRef} className="waveform-canvas" role="img" aria-label={label} />;
}
