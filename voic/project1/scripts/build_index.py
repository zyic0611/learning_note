#!/usr/bin/env python3
"""批量建库：把 songs 目录里所有歌提取成 .sig 特征指纹。"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mirtool.pipeline import build_library  # noqa: E402


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = argparse.ArgumentParser(description="从歌曲目录批量提取特征指纹")
    p.add_argument("--songs", default=os.path.join(here, "data/songs"))
    p.add_argument("--sig", default=os.path.join(here, "data/sig"))
    p.add_argument("--clip", default=os.path.join(here, "data/clips"))
    p.add_argument("--seconds", type=float, default=30.0)
    p.add_argument("--k", type=int, default=16)
    p.add_argument("--cmn", action="store_true", help="启用倒谱均值归一化")
    args = p.parse_args()

    print("扫描 %s ..." % args.songs)
    done, failed = build_library(args.songs, args.sig, args.clip,
                                 seconds=args.seconds, k=args.k, cmn=args.cmn)
    print("\n完成：%d 首入库，%d 首失败" % (len(done), len(failed)))
    for name, err in failed:
        print("  失败 %s: %s" % (name, err))
    print("特征库 -> %s" % args.sig)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
