"""音频读取：任何格式 -> 16kHz 单声道 float32 波形。

WAV 用 Python 标准库直接读（无需外部依赖）；
MP3/FLAC/M4A 等走 ffmpeg（优先用 imageio-ffmpeg 自带的静态二进制）。
"""
import os
import re
import subprocess
import wave

import numpy as np

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None

TARGET_FS = 16000


def _ffmpeg_exe():
    return imageio_ffmpeg.get_ffmpeg_exe() if imageio_ffmpeg else "ffmpeg"


def _load_wav_stdlib(path, fs, max_seconds=None):
    with wave.open(path, "rb") as w:
        if w.getframerate() != fs or w.getnchannels() != 1:
            raise ValueError("需要交给 ffmpeg 重采样/降混")
        width = w.getsampwidth()
        count = w.getnframes()
        if max_seconds is not None:
            count = min(count, int(round(max_seconds * fs)))
            w.setpos(max(0, (w.getnframes() - count) // 2))
        raw = w.readframes(count)
    if width == 2:
        x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 4:
        x = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    elif width == 1:
        x = (np.frombuffer(raw, dtype="u1").astype(np.float32) - 128.0) / 128.0
    else:
        raise ValueError("不支持的采样位宽: %d" % width)
    return x, fs


def _probe_duration(path, exe):
    """通过 ffmpeg 的输入信息读取时长；无法读取时返回 None。"""
    p = subprocess.run([exe, "-hide_banner", "-i", path], stdout=subprocess.DEVNULL,
                       stderr=subprocess.PIPE, check=False)
    text = p.stderr.decode("utf-8", "ignore")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if not m:
        return None
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def _load_ffmpeg(path, fs, max_seconds=None):
    exe = _ffmpeg_exe()
    try:
        duration = _probe_duration(path, exe) if max_seconds is not None else None
        cmd = [exe, "-v", "error"]
        if duration is not None and duration > max_seconds:
            cmd += ["-ss", "%.6f" % ((duration - max_seconds) / 2.0)]
        cmd += ["-i", path]
        if max_seconds is not None:
            cmd += ["-t", str(max_seconds)]
        cmd += ["-f", "s16le", "-acodec", "pcm_s16le", "-ac", "1", "-ar", str(fs), "-"]
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except FileNotFoundError:
        raise RuntimeError("读 %s 需要 ffmpeg，但没找到。请安装 ffmpeg 或 pip install imageio-ffmpeg" % path)
    except subprocess.CalledProcessError as e:
        raise RuntimeError("ffmpeg 解码失败 %s: %s" % (path, e.stderr.decode("utf-8", "ignore")[:300]))
    return np.frombuffer(p.stdout, dtype="<i2").astype(np.float32) / 32768.0, fs


def load_audio(path, fs=TARGET_FS, max_seconds=None):
    """读取音频，返回 (波形 float32, 采样率)。

    max_seconds 给定时，只解码音频中间这段时长，避免长压缩音频在内存中展开。
    """
    if os.path.splitext(path)[1].lower() == ".wav":
        try:
            return _load_wav_stdlib(path, fs, max_seconds)
        except (wave.Error, ValueError, EOFError):
            pass  # 格式、采样率或声道数不符，交给 ffmpeg
    return _load_ffmpeg(path, fs, max_seconds)


def center_segment(x, fs, seconds=30.0):
    """取整首歌中间总计 seconds 秒（默认 30 秒，和原文一致）。

    整首歌做 MFCC 计算量太大，且首尾常有静音/淡入淡出，中间段更有代表性。
    若歌曲不足 seconds 秒，就直接返回整首歌。
    """
    n = len(x)
    length = min(n, int(round(fs * seconds)))
    start = max(0, (n - length) // 2)
    return x[start:start + length]


def write_wav(path, x, fs=TARGET_FS):
    """写 16-bit 单声道 WAV。"""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    y = np.clip(x, -1.0, 1.0)
    pcm = (y * 32767.0).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(fs)
        w.writeframes(pcm.tobytes())
