#!/usr/bin/env python3
"""合成一个演示用的"歌曲库"。

为什么要自己合成：原文那 500 首 MP3 有版权不能分享，这里用加法合成造一批
"听起来像那么回事"的小曲子，好处是我们知道每首歌的真实归属（音色家族），
所以除了能试听，还能算出检索准确率。

每个家族 = 一种音色（谐波成分 + 包络 + 有没有鼓），同家族内的歌在调性、
和声进行、旋律、速度上都不同 —— 也就是说"家族"这个信息只能从音色里看出来，
系统里没有任何地方用到文件名或标签。
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mirtool.audio import write_wav, TARGET_FS  # noqa: E402

FS = TARGET_FS
DUR = 40.0            # 每首 40 秒，保证中间 30 秒是完整的音乐
N_PER_FAMILY = 8

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
}
# 和声进行（音阶级数，0 起）
PROGRESSIONS = [
    [0, 4, 5, 3], [0, 3, 4, 4], [5, 3, 0, 4], [0, 5, 3, 4], [1, 4, 0, 0],
]


def hz(midi):
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def scale_note(key, scale, degree):
    return key + scale[degree % len(scale)] + 12 * (degree // len(scale))


# 每个家族的音色配方
FAMILIES = {
    "钢琴": dict(
        artist="林知远", scale="major", bpm=(72, 96), attack=0.004,
        decay=3.2, release=0.08, noise=0.0, vibrato=0.0, hmax=14, drums=False,
        harm=lambda h: 1.0 / h ** 1.5,
    ),
    "电钢琴": dict(   # 和钢琴很像，故意做成"容易混"的一对
        artist="陈亦白", scale="major", bpm=(76, 100), attack=0.010,
        decay=1.6, release=0.12, noise=0.0, vibrato=0.0, hmax=8, drums=False,
        harm=lambda h: 1.0 / h ** 2.6,
    ),
    "木吉他": dict(
        artist="苏木野", scale="major", bpm=(96, 126), attack=0.002,
        decay=2.0, release=0.06, noise=0.03, vibrato=0.0, hmax=18, drums=False,
        harm=lambda h: (1.0 / h ** 1.2) * (1.0 + 0.7 * np.exp(-((h - 3) ** 2) / 2.0)),
    ),
    "弦乐": dict(
        artist="关山月", scale="minor", bpm=(60, 78), attack=0.130,
        decay=0.0, release=0.30, noise=0.008, vibrato=5.5, hmax=22, drums=False,
        harm=lambda h: 1.0 / h ** 2.0,
    ),
    "长笛": dict(
        artist="白鹭", scale="major", bpm=(80, 100), attack=0.060,
        decay=0.0, release=0.18, noise=0.10, vibrato=5.0, hmax=4, drums=False,
        harm=lambda h: 1.0 if h == 1 else (0.12 if h == 2 else 0.03),
    ),
    "合成器": dict(
        artist="NEON-9", scale="minor", bpm=(118, 140), attack=0.006,
        decay=0.0, release=0.10, noise=0.0, vibrato=0.0, hmax=26, drums=True,
        harm=lambda h: 1.0 / h,   # 锯齿波，谐波丰富
    ),
}

TITLES = {
    "钢琴": ["雨后的琴键", "旧日回响", "午后三点的光", "给冬天的信", "纸飞机",
             "屋檐下的猫", "未寄出的明信片", "第七个夏天"],
    "电钢琴": ["蓝色房间", "凌晨两点半", "慢速列车", "玻璃海", "安静的爆炸",
               "二十四小时便利店", "雾中散步", "褪色的胶片"],
    "木吉他": ["公路电影", "八月的风", "去往南方", "无名小镇", "篝火旁",
               "把夏天留下", "背包客", "远山的回声"],
    "弦乐": ["挽歌", "雪落无声", "断章", "长夜将至", "失语者",
             "灰色的海", "旧城", "安魂曲"],
    "长笛": ["山谷晨雾", "第一缕阳光", "溪水", "春分", "青鸟",
             "风穿过竹林", "浮云", "白桦林"],
    "合成器": ["霓虹脉冲", "数据洪流", "午夜跑道", "人造日落", "信号丢失",
               "赛博花园", "电子羊", "超频"],
}


def render_note(freq, dur, spec, amp, rng):
    """加法合成一个音符。"""
    n = max(1, int(dur * FS))
    t = np.arange(n) / FS

    env = np.ones(n)
    na = max(1, int(spec["attack"] * FS))
    env[:na] = np.linspace(0.0, 1.0, na)
    if spec["decay"] > 0:
        env = env * np.exp(-spec["decay"] * t)
    nr = min(n, max(1, int(spec["release"] * FS)))
    env[-nr:] *= np.linspace(1.0, 0.0, nr)

    y = np.zeros(n)
    hmax = min(spec["hmax"], max(1, int(0.45 * FS / max(freq, 20.0))))
    for h in range(1, hmax + 1):
        a = spec["harm"](h)
        if a < 1e-3:
            continue
        phase = rng.uniform(0, 2 * np.pi)
        if spec["vibrato"] > 0:
            y += a * np.sin(2 * np.pi * freq * h * t
                            + 0.02 * h * np.sin(2 * np.pi * spec["vibrato"] * t)
                            + phase)
        else:
            y += a * np.sin(2 * np.pi * freq * h * t + phase)

    if spec["noise"] > 0:
        y += spec["noise"] * rng.standard_normal(n)

    return amp * y * env


def render_kick(rng):
    n = int(0.18 * FS)
    t = np.arange(n) / FS
    f = 55.0 + 90.0 * np.exp(-28.0 * t)
    return 0.55 * np.sin(2 * np.pi * f * t) * np.exp(-16.0 * t)


def render_hat(rng):
    n = int(0.05 * FS)
    t = np.arange(n) / FS
    return 0.10 * rng.standard_normal(n) * np.exp(-70.0 * t)


def render_song(family, rng):
    spec = FAMILIES[family]
    bpm = rng.uniform(*spec["bpm"])
    beat = 60.0 / bpm
    key = int(rng.integers(48, 61))
    scale = SCALES[spec["scale"]]
    prog = PROGRESSIONS[int(rng.integers(len(PROGRESSIONS)))]

    n = int(DUR * FS)
    y = np.zeros(n)

    def add(sig, start):
        s = int(start * FS)
        if s >= n:
            return
        e = min(n, s + len(sig))
        y[s:e] += sig[:e - s]

    total_beats = DUR / beat
    b = 0
    while b + 4 <= total_beats:
        deg = prog[(b // 4) % len(prog)]
        root = scale_note(key, scale, deg)

        for k in (0, 2, 4):
            f = hz(scale_note(key, scale, deg + k))
            add(render_note(f, beat * 4.0, spec, 0.20, rng), b * beat)

        add(render_note(hz(root - 12), beat * 2.0, spec, 0.34, rng), b * beat)
        add(render_note(hz(root - 12), beat * 2.0, spec, 0.30, rng), (b + 2) * beat)

        for m in range(4):
            if rng.random() < 0.22:
                continue
            d = int(rng.integers(0, 7))
            oct_up = 12 if rng.random() < 0.4 else 0
            dur = beat * float(rng.choice([1.0, 1.0, 2.0]))
            add(render_note(hz(scale_note(key, scale, d) + 12 + oct_up),
                            dur, spec, 0.26, rng), (b + m) * beat)

        if spec["drums"]:
            for k in range(4):
                add(render_kick(rng), (b + k) * beat)
                add(render_hat(rng), (b + k + 0.5) * beat)
        b += 4

    peak = np.abs(y).max()
    if peak > 0:
        y = 0.9 * y / peak
    fade = int(0.5 * FS)
    y[:fade] *= np.linspace(0.0, 1.0, fade)
    y[-fade:] *= np.linspace(1.0, 0.0, fade)
    return y, dict(bpm=round(bpm, 1), key_midi=key)


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = argparse.ArgumentParser(description="合成演示歌曲库")
    p.add_argument("--out", default=os.path.join(here, "data/songs"))
    p.add_argument("--meta", default=os.path.join(here, "data/meta.json"))
    p.add_argument("--per-family", type=int, default=N_PER_FAMILY)
    p.add_argument("--seed", type=int, default=2026)
    args = p.parse_args()

    os.makedirs(args.out, exist_ok=True)
    existing_songs = {}
    if os.path.isfile(args.meta):
        try:
            with open(args.meta, encoding="utf-8") as f:
                existing = json.load(f)
            existing_songs = existing.get("songs", {})
        except (OSError, ValueError):
            pass
    meta = {"_note": "演示库：合成音频。family 是真实的音色家族（检索系统的 ground truth），"
                     "检索过程本身完全不使用 title/artist/family。",
            "songs": dict(existing_songs)}
    total = 0
    for fi, (family, spec) in enumerate(FAMILIES.items()):
        for i in range(args.per_family):
            rng = np.random.default_rng(args.seed + fi * 100 + i)
            name = "%s-%02d" % (family, i + 1)
            y, info = render_song(family, rng)
            write_wav(os.path.join(args.out, name + ".wav"), y, FS)
            meta["songs"][name] = dict(
                title=TITLES[family][i % len(TITLES[family])],
                artist=spec["artist"], family=family,
                bpm=info["bpm"], key_midi=info["key_midi"],
            )
            total += 1
            print("  %-12s %-14s %-8s %.0f BPM" % (name, meta["songs"][name]["title"],
                                                   spec["artist"], info["bpm"]))
    with open(args.meta, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print("\n共生成 %d 首，%d 个家族 -> %s" % (total, len(FAMILIES), args.out))
    print("元数据 -> %s" % args.meta)


if __name__ == "__main__":
    main()
