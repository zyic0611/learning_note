const TARGET_SAMPLE_RATE = 16_000;

export class StreamingPcm16Resampler {
  private readonly ratio: number;
  private buffer = new Float32Array(0);
  private position = 0;

  constructor(sourceSampleRate: number, targetSampleRate = TARGET_SAMPLE_RATE) {
    if (!Number.isFinite(sourceSampleRate) || sourceSampleRate <= 0) {
      throw new Error('无效的音频采样率');
    }
    this.ratio = sourceSampleRate / targetSampleRate;
  }

  push(input: Float32Array): ArrayBuffer {
    if (input.length === 0) return new ArrayBuffer(0);

    const merged = new Float32Array(this.buffer.length + input.length);
    merged.set(this.buffer);
    merged.set(input, this.buffer.length);

    const output: number[] = [];
    while (this.position + 1 < merged.length) {
      const left = Math.floor(this.position);
      const fraction = this.position - left;
      const sample = merged[left] + (merged[left + 1] - merged[left]) * fraction;
      output.push(sample);
      this.position += this.ratio;
    }

    const consumed = Math.floor(this.position);
    this.buffer = merged.slice(Math.min(consumed, merged.length));
    this.position -= consumed;
    return float32ToPcm16(new Float32Array(output));
  }

  reset(): void {
    this.buffer = new Float32Array(0);
    this.position = 0;
  }
}

export function float32ToPcm16(samples: Float32Array): ArrayBuffer {
  const buffer = new ArrayBuffer(samples.length * 2);
  const view = new DataView(buffer);
  for (let index = 0; index < samples.length; index += 1) {
    const clamped = Math.max(-1, Math.min(1, samples[index]));
    const pcm = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
    view.setInt16(index * 2, Math.round(pcm), true);
  }
  return buffer;
}

export function mixToMono(inputBuffer: AudioBuffer): Float32Array {
  const mono = new Float32Array(inputBuffer.length);
  for (let channel = 0; channel < inputBuffer.numberOfChannels; channel += 1) {
    const data = inputBuffer.getChannelData(channel);
    for (let index = 0; index < data.length; index += 1) {
      mono[index] += data[index] / inputBuffer.numberOfChannels;
    }
  }
  return mono;
}

export function formatDuration(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(safe / 60).toString().padStart(2, '0');
  const remainder = (safe % 60).toString().padStart(2, '0');
  return `${minutes}:${remainder}`;
}

export async function readAudioWaveform(file: Blob, points = 900): Promise<{ waveform: number[]; duration: number }> {
  const context = new AudioContext();
  try {
    const data = await file.arrayBuffer();
    const audio = await context.decodeAudioData(data.slice(0));
    const mono = mixToMono(audio);
    const bucketSize = Math.max(1, Math.floor(mono.length / points));
    const waveform: number[] = [];
    for (let start = 0; start < mono.length; start += bucketSize) {
      let peak = 0;
      const end = Math.min(start + bucketSize, mono.length);
      for (let index = start; index < end; index += 1) {
        if (Math.abs(mono[index]) > Math.abs(peak)) peak = mono[index];
      }
      waveform.push(peak);
    }
    return { waveform, duration: audio.duration };
  } finally {
    await context.close();
  }
}

export function getSupportedRecordingMimeType(): string | undefined {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type));
}
