"""相似歌曲检索：拿一首查询歌的特征，和库里每首歌算 EMD，按距离排序。

库只有几百首，直接线性扫描就够了（原文也是这么做的）。
"""
import argparse
import os
import sys

from .audio import TARGET_FS, write_wav
from .distance import emd
from .pipeline import (load_index_config, load_meta, load_signatures,
                       signature_from_audio)
from .report import write_html


def rank(query_sig, library, top=None, exclude=None):
    """返回 [(名字, EMD), ...]，按 EMD 升序。"""
    scored = []
    for name, sig in library.items():
        if name == exclude:
            continue
        scored.append((name, emd(query_sig, sig)))
    scored.sort(key=lambda x: x[1])
    return scored[:top] if top else scored


def print_table(results, meta=None, query_family=None, limit=10):
    meta = meta or {}
    print("%-5s %-10s %-30s %-12s %s" % ("排名", "EMD", "歌曲", "家族", "命中"))
    for i, (name, e) in enumerate(results[:limit], 1):
        fam = meta.get(name, {}).get("family", "")
        hit = "✓" if (query_family and fam == query_family) else ""
        print("%-5d %-10.2f %-30s %-12s %s" % (i, e, name, fam, hit))


def resolve_query(query, songs_dir, library, seconds, k, cmn):
    """query 可以是一个音频文件路径，也可以是库里的歌名。"""
    if os.path.isfile(query):
        name = os.path.splitext(os.path.basename(query))[0]
        if name in library:
            name += "-上传查询"
        sig, segment = signature_from_audio(query, seconds=seconds, k=k, cmn=cmn)
        return name, sig, segment, True
    if query in library:
        return query, library[query], None, False
    raise SystemExit("找不到查询歌曲 %r：既不是文件，也不在特征库里。" % query)


def main(argv=None):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = argparse.ArgumentParser(description="相似歌曲检索（MFCC + VQ + EMD）")
    p.add_argument("--query", required=True, help="音频文件路径，或库里的歌名")
    p.add_argument("--songs", default=os.path.join(here, "data/songs"), help="原始歌曲目录")
    p.add_argument("--sig", default=os.path.join(here, "data/sig"), help="特征库目录")
    p.add_argument("--clip", default=os.path.join(here, "data/clips"), help="中间段 wav 目录")
    p.add_argument("--meta", default=os.path.join(here, "data/meta.json"))
    p.add_argument("--out", default=os.path.join(here, "out/result.html"))
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--seconds", type=float, default=None, help="取中间多少秒（默认读取建库配置）")
    p.add_argument("--k", type=int, default=None, help="聚类数（默认读取建库配置）")
    cmn_group = p.add_mutually_exclusive_group()
    cmn_group.add_argument("--cmn", dest="cmn", action="store_true", help="启用倒谱均值归一化")
    cmn_group.add_argument("--no-cmn", dest="cmn", action="store_false", help="禁用倒谱均值归一化")
    p.set_defaults(cmn=None)
    p.add_argument("--no-html", action="store_true")
    args = p.parse_args(argv)

    library = load_signatures(args.sig)
    if not library:
        raise SystemExit("特征库 %s 是空的，先跑 scripts/build_index.py 建库。" % args.sig)
    meta = load_meta(args.meta)
    config = load_index_config(args.sig)
    seconds = float(config["seconds"] if args.seconds is None else args.seconds)
    k = int(config["k"] if args.k is None else args.k)
    cmn = bool(config["cmn"] if args.cmn is None else args.cmn)

    name, sig, query_segment, is_external = resolve_query(
        args.query, args.songs, library, seconds, k, cmn)
    exclude = None if is_external else name
    results = rank(sig, library, exclude=exclude)

    fam = meta.get(name, {}).get("family")
    print("\n查询：%s%s   库大小：%d 首\n" % (name, "（家族：%s）" % fam if fam else "", len(library)))
    print_table(results, meta, fam, limit=args.top)

    if not args.no_html:
        if query_segment is not None:
            write_wav(os.path.join(args.clip, name + ".wav"), query_segment, TARGET_FS)
        write_html(args.out, name, results, meta=meta, clip_dir=args.clip,
                   songs_dir=args.songs, top=args.top, seconds=seconds,
                   cmn=cmn, k=k)
        print("\nHTML 结果页：%s" % args.out)
        print("用浏览器打开它就能直接试听对比（也可以 python -m http.server 起个服务）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
