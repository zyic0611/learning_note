"""把上面几步串起来：音频文件 -> 特征指纹；一个目录 -> 一个特征库。"""
import json
import os

import numpy as np

from .audio import load_audio, center_segment, write_wav, TARGET_FS
from .mfcc import DIM, FRAME_HOP, extract_mfcc
from .signature import build_signature, Signature

AUDIO_EXT = (".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma")
INDEX_CONFIG = "_index.json"


def signature_from_audio(path, seconds=30.0, k=16, cmn=False, seed=0, n_init=5):
    """音频 -> (Signature, 中间段波形)。"""
    # 解码阶段就限制为中间 seconds 秒，避免先把数小时压缩音频全部展开进内存。
    x, fs = load_audio(path, TARGET_FS, max_seconds=seconds)
    seg = center_segment(x, fs, seconds)
    if len(seg) == 0:
        raise RuntimeError("音频太短或读取失败: %s" % path)
    if float(np.std(seg)) < 1e-5:
        raise RuntimeError("音频几乎是静音，无法提取有效特征: %s" % path)
    min_samples = k * FRAME_HOP
    if len(seg) < min_samples:
        raise RuntimeError("音频太短：至少需要 %.2f 秒才能建立 %d 类指纹" %
                           (min_samples / float(fs), k))
    mfcc = extract_mfcc(seg, fs, cmn=cmn)
    sig = build_signature(mfcc, k=k, seed=seed, n_init=n_init)
    return sig, seg


def song_files(songs_dir):
    """返回 {歌曲名: 绝对路径}，只接受支持的音频扩展名。"""
    if not os.path.isdir(songs_dir):
        return {}
    songs = {}
    for filename in sorted(os.listdir(songs_dir)):
        if not filename.lower().endswith(AUDIO_EXT):
            continue
        name = os.path.splitext(filename)[0]
        if name in songs:
            raise ValueError("歌曲文件名去掉扩展名后重复: %s" % name)
        songs[name] = os.path.join(songs_dir, filename)
    return songs


def list_songs(songs_dir):
    return sorted(song_files(songs_dir))


def _remove_stale_files(directory, suffix, current_names):
    if not os.path.isdir(directory):
        return
    for filename in os.listdir(directory):
        if not filename.endswith(suffix):
            continue
        if filename[:-len(suffix)] not in current_names:
            os.remove(os.path.join(directory, filename))


def save_index_config(sig_dir, seconds, k, cmn):
    config = {
        "version": 1,
        "sample_rate": TARGET_FS,
        "seconds": float(seconds),
        "mfcc_dim": DIM,
        "k": int(k),
        "cmn": bool(cmn),
    }
    with open(os.path.join(sig_dir, INDEX_CONFIG), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def load_index_config(sig_dir):
    path = os.path.join(sig_dir, INDEX_CONFIG)
    if not os.path.isfile(path):
        return {"version": 1, "sample_rate": TARGET_FS, "seconds": 30.0,
                "mfcc_dim": DIM, "k": 16, "cmn": False}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_library(songs_dir, sig_dir, clip_dir,
                  seconds=30.0, k=16, cmn=False, verbose=True):
    """批量提取：songs_dir 里的每首歌 -> sig_dir/<name>.sig，中间段存 clip_dir/<name>.wav。"""
    os.makedirs(sig_dir, exist_ok=True)
    os.makedirs(clip_dir, exist_ok=True)
    files = song_files(songs_dir)
    current_names = set(files)
    _remove_stale_files(sig_dir, ".sig", current_names)
    _remove_stale_files(clip_dir, ".wav", current_names)

    done, failed = [], []
    for name, path in files.items():
        sig_path = os.path.join(sig_dir, name + ".sig")
        clip_path = os.path.join(clip_dir, name + ".wav")
        tmp_sig = sig_path + ".tmp"
        tmp_clip = clip_path + ".tmp.wav"
        try:
            sig, seg = signature_from_audio(path, seconds=seconds, k=k, cmn=cmn)
            sig.save(tmp_sig)
            write_wav(tmp_clip, seg, TARGET_FS)
            # 两个新文件都成功后才替换旧索引，单曲解码失败不会破坏上次可用结果。
            os.replace(tmp_sig, sig_path)
            os.replace(tmp_clip, clip_path)
            done.append(name)
            if verbose:
                print("  %-28s -> %s.sig" % (name, name))
        except Exception as e:
            for tmp_path in (tmp_sig, tmp_clip):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            failed.append((name, str(e)))
            if verbose:
                print("  %-28s 跳过: %s" % (name, e))
    save_index_config(sig_dir, seconds, k, cmn)
    return done, failed


def load_meta(meta_path):
    """读取元数据，并统一返回 {歌曲名: 信息}。

    演示库文件额外带有说明字段，所以歌曲信息放在 songs 下；用户自己写的
    简单元数据也可以直接使用扁平结构。
    """
    if meta_path and os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        return meta.get("songs", meta)
    return {}


def load_signatures(sig_dir):
    """读取一个特征库目录，返回 {名字: Signature}；目录不存在时返回空库。"""
    if not os.path.isdir(sig_dir):
        return {}
    out = {}
    for f in sorted(os.listdir(sig_dir)):
        if f.endswith(".sig"):
            out[f[:-4]] = Signature.load(os.path.join(sig_dir, f))
    return out
