#!/usr/bin/env python3
"""全库检索评估。

让每首歌曲轮流当查询，排除它自己；与查询歌曲同 family 的其余歌曲视为相关结果。
计算：
  Top-1 Accuracy：第 1 名是否同家族
  Precision@5：前 5 名中同家族歌曲的比例
  Recall@5：该家族其余歌曲中，有多少被前 5 名找回
  mAP：对每个查询计算 Average Precision，再取平均

注意：family 只用于最后评分，特征提取和检索完全没有读取它，不存在标签泄漏。
"""
import argparse
import hashlib
import html
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mirtool.distance import emd  # noqa: E402
from mirtool.pipeline import load_meta, load_signatures  # noqa: E402


def signature_fingerprint(names, library):
    """哈希实际指纹内容；同名歌曲重建后也会得到不同缓存键。"""
    h = hashlib.sha256()
    for name in names:
        sig = library[name]
        h.update(name.encode("utf-8"))
        h.update(np.asarray(sig.to_matrix(), dtype="<f8").tobytes())
    return h.hexdigest()


def distance_matrix(names, library, cache_path=None):
    """计算对称距离矩阵；仅当歌曲名和指纹内容均一致时读取缓存。"""
    fingerprint = signature_fingerprint(names, library)
    if cache_path and os.path.exists(cache_path):
        z = np.load(cache_path, allow_pickle=False)
        cached_names = [str(x) for x in z["names"]]
        cached_fingerprint = str(z["fingerprint"]) if "fingerprint" in z.files else ""
        if (cached_names == names and cached_fingerprint == fingerprint
                and z["dist"].shape == (len(names), len(names))):
            return z["dist"], True

    n = len(names)
    D = np.zeros((n, n), dtype=np.float64)
    total = n * (n - 1) // 2
    done = 0
    started = time.time()
    for i in range(n):
        for j in range(i + 1, n):
            D[i, j] = D[j, i] = emd(library[names[i]], library[names[j]])
            done += 1
        if (i + 1) % 4 == 0 or i == n - 1:
            elapsed = time.time() - started
            print("  距离计算 %4d/%d（%5.1f%%，%.1f 秒）" %
                  (done, total, 100.0 * done / max(1, total), elapsed), flush=True)

    if cache_path:
        os.makedirs(os.path.dirname(os.path.abspath(cache_path)), exist_ok=True)
        np.savez_compressed(cache_path, names=np.array(names), dist=D,
                            fingerprint=np.array(fingerprint))
    return D, False


def average_precision(relevant):
    """relevant[r] 表示第 r+1 名是否相关。"""
    relevant = np.asarray(relevant, dtype=bool)
    total_rel = int(relevant.sum())
    if total_rel == 0:
        return 0.0
    ranks = np.arange(1, len(relevant) + 1)
    precisions = np.cumsum(relevant) / ranks
    return float(precisions[relevant].sum() / total_rel)


def evaluate(names, D, meta, k=5):
    rows = []
    by_family = {}
    for i, name in enumerate(names):
        family = meta.get(name, {}).get("family")
        if not family:
            raise ValueError("%s 缺少 family，无法做有监督评估" % name)
        order = np.argsort(D[i])
        order = [j for j in order if j != i]
        ranked = [names[j] for j in order]
        rel = np.array([meta.get(n, {}).get("family") == family for n in ranked])
        n_rel = int(rel.sum())
        topk_rel = int(rel[:k].sum())
        row = {
            "name": name,
            "title": meta.get(name, {}).get("title", name),
            "family": family,
            "top1": bool(rel[0]) if len(rel) else False,
            "precision_at_k": topk_rel / float(k),
            "recall_at_k": topk_rel / float(n_rel) if n_rel else 0.0,
            "ap": average_precision(rel),
            "ranking": [
                {"name": ranked[r], "distance": float(D[i, order[r]]),
                 "family": meta.get(ranked[r], {}).get("family", ""),
                 "relevant": bool(rel[r])}
                for r in range(min(10, len(ranked)))
            ],
        }
        rows.append(row)
        by_family.setdefault(family, []).append(row)

    def summary(items):
        return {
            "queries": len(items),
            "top1_accuracy": float(np.mean([r["top1"] for r in items])),
            "precision_at_k": float(np.mean([r["precision_at_k"] for r in items])),
            "recall_at_k": float(np.mean([r["recall_at_k"] for r in items])),
            "map": float(np.mean([r["ap"] for r in items])),
        }

    return summary(rows), {f: summary(rs) for f, rs in sorted(by_family.items())}, rows


def write_json(path, metrics, families, rows, k):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    data = {"k": k, "overall": metrics, "by_family": families, "queries": rows}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def pct(x):
    return "%.1f%%" % (100.0 * x)


def write_html(path, metrics, families, rows, k):
    """生成无第三方 JS/CSS 的离线评估页；统计卡 + 表格比花哨图更适合答辩解释。"""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    lines = []
    a = lines.append
    a("<!doctype html><html lang='zh'><head><meta charset='utf-8'>")
    a("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    a("<title>相似歌曲检索系统 - 评估报告</title>")
    a("""<style>
:root{--bg:#f7f8fa;--surface:#fff;--ink:#172033;--muted:#657086;--line:#e6e9ef;
      --blue:#2563eb;--blue-soft:#e8f0ff;--good:#16794b;--good-soft:#e7f7ef}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.55 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
main{max-width:1120px;margin:36px auto;padding:0 20px 60px}h1{font-size:26px;margin:0 0 4px}
h2{font-size:18px;margin:28px 0 12px}.sub{color:var(--muted);margin-bottom:22px}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.card{background:var(--surface);
border:1px solid var(--line);border-radius:12px;padding:18px}.metric{font-size:30px;font-weight:720;
letter-spacing:-.5px}.label{color:var(--muted);font-size:13px}.note{margin-top:18px;padding:14px 16px;
background:var(--blue-soft);border-radius:9px;color:#244477}table{width:100%;border-collapse:collapse;
background:var(--surface);border:1px solid var(--line);font-size:13px}th,td{padding:9px 10px;
border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{background:#f1f3f7;
font-weight:650;position:sticky;top:0}td.num{font-variant-numeric:tabular-nums}.good{color:var(--good);
font-weight:650}.bad{color:#b42318;font-weight:650}.rank{white-space:nowrap}.hit{background:var(--good-soft);
border-radius:4px;padding:1px 5px}.miss{color:var(--muted)}details{margin:0}summary{cursor:pointer;color:var(--blue)}
.explain{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.explain div{background:var(--surface);
border:1px solid var(--line);padding:13px 15px;border-radius:9px}.formula{font-family:ui-monospace,SFMono-Regular,
Menlo,monospace;color:#334155}@media(max-width:760px){.cards{grid-template-columns:repeat(2,1fr)}
.explain{grid-template-columns:1fr}.wide{overflow-x:auto}}
</style></head><body><main>""")
    a("<h1>相似歌曲检索系统 · 评估报告</h1>")
    a("<div class='sub'>48 首合成演示歌曲，6 个音色家族；每首歌轮流作查询并排除自身。标签只用于评分，不参与检索。</div>")
    a("<section class='cards'>")
    for label, key in [("Top-1 准确率", "top1_accuracy"),
                       ("Precision@%d" % k, "precision_at_k"),
                       ("Recall@%d" % k, "recall_at_k"), ("mAP", "map")]:
        a("<div class='card'><div class='metric'>%s</div><div class='label'>%s</div></div>" %
          (pct(metrics[key]), html.escape(label)))
    a("</section>")
    a("<div class='note'>本项目刻意只使用 MFCC 音色特征，因此评价目标是找回同一“音色家族”，不是判断旋律是否完全相同。数值越高越好。</div>")

    a("<h2>四个指标怎么解释</h2><section class='explain'>")
    a("<div><b>Top-1 准确率</b><br>第一名属于同家族的查询占比。最适合演示时一句话说明。</div>")
    a("<div><b>Precision@%d</b><br><span class='formula'>前 %d 名中的相关歌曲数 ÷ %d</span>，衡量结果列表干不干净。</div>" % (k, k, k))
    a("<div><b>Recall@%d</b><br><span class='formula'>前 %d 名中的相关歌曲数 ÷ 该家族其余歌曲数</span>，衡量找回了多少。</div>" % (k, k))
    a("<div><b>mAP</b><br>综合观察所有排名位置；相关歌曲越集中在前面，分数越高。</div>")
    a("</section>")

    a("<h2>按音色家族</h2><div class='wide'><table><thead><tr><th>家族</th><th>查询数</th><th>Top-1</th><th>P@%d</th><th>R@%d</th><th>mAP</th></tr></thead><tbody>" % (k, k))
    for family, m in families.items():
        a("<tr><td><b>%s</b></td><td>%d</td><td class='num'>%s</td><td class='num'>%s</td><td class='num'>%s</td><td class='num'>%s</td></tr>" %
          (html.escape(family), m["queries"], pct(m["top1_accuracy"]),
           pct(m["precision_at_k"]), pct(m["recall_at_k"]), pct(m["map"])))
    a("</tbody></table></div>")

    a("<h2>逐首查询结果</h2><div class='wide'><table><thead><tr><th>查询</th><th>家族</th><th>Top-1</th><th>P@%d</th><th>R@%d</th><th>AP</th><th>前 10 名</th></tr></thead><tbody>" % (k, k))
    for r in rows:
        ranking = []
        for i, x in enumerate(r["ranking"], 1):
            cls = "hit" if x["relevant"] else "miss"
            ranking.append("<span class='%s'>%d. %s [%s] %.1f</span>" %
                           (cls, i, html.escape(x["name"]), html.escape(x["family"]), x["distance"]))
        a("<tr><td><b>%s</b><br><span class='label'>%s</span></td><td>%s</td>"
          "<td class='%s'>%s</td><td class='num'>%s</td><td class='num'>%s</td><td class='num'>%s</td>"
          "<td class='rank'><details><summary>查看排名</summary>%s</details></td></tr>" %
          (html.escape(r["name"]), html.escape(r["title"]), html.escape(r["family"]),
           "good" if r["top1"] else "bad", "命中" if r["top1"] else "未命中",
           pct(r["precision_at_k"]), pct(r["recall_at_k"]), pct(r["ap"]),
           "<br>".join(ranking)))
    a("</tbody></table></div>")
    a("</main></body></html>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = argparse.ArgumentParser(description="评估相似歌曲检索效果")
    p.add_argument("--sig", default=os.path.join(here, "data/sig"))
    p.add_argument("--meta", default=os.path.join(here, "data/meta.json"))
    p.add_argument("--cache", default=os.path.join(here, "out/distances.npz"))
    p.add_argument("--json", default=os.path.join(here, "out/evaluation.json"))
    p.add_argument("--html", default=os.path.join(here, "out/evaluation.html"))
    p.add_argument("-k", type=int, default=5)
    p.add_argument("--recompute", action="store_true")
    p.add_argument("--skip-if-unlabeled", action="store_true",
                   help="存在无 family 标签歌曲时清除旧指标并跳过评估")
    args = p.parse_args()

    library = load_signatures(args.sig)
    meta = load_meta(args.meta)
    names = sorted(library)
    if len(names) < 2:
        raise SystemExit("特征库至少需要两首歌")
    unlabeled = [name for name in names if not meta.get(name, {}).get("family")]
    if unlabeled and args.skip_if_unlabeled:
        for path in (args.cache, args.json, args.html):
            if os.path.exists(path):
                os.remove(path)
        print("跳过评估：%d 首歌曲没有 family 标签（检索功能不受影响）。" % len(unlabeled))
        return
    if unlabeled:
        raise SystemExit("以下歌曲缺少 family，无法做有监督评估：%s" % "、".join(unlabeled[:8]))
    print("评估 %d 首歌曲（%d 对距离）..." % (len(names), len(names) * (len(names) - 1) // 2))
    cache = None if args.recompute else args.cache
    D, cached = distance_matrix(names, library, cache)
    if args.recompute:
        os.makedirs(os.path.dirname(os.path.abspath(args.cache)), exist_ok=True)
        np.savez_compressed(args.cache, names=np.array(names), dist=D,
                            fingerprint=np.array(signature_fingerprint(names, library)))
    print("距离矩阵：%s" % ("读取缓存" if cached else "重新计算完成"))

    metrics, families, rows = evaluate(names, D, meta, args.k)
    write_json(args.json, metrics, families, rows, args.k)
    write_html(args.html, metrics, families, rows, args.k)
    print("\n整体结果")
    print("  Top-1 Accuracy : %s" % pct(metrics["top1_accuracy"]))
    print("  Precision@%d    : %s" % (args.k, pct(metrics["precision_at_k"])))
    print("  Recall@%d       : %s" % (args.k, pct(metrics["recall_at_k"])))
    print("  mAP            : %s" % pct(metrics["map"]))
    print("\nJSON -> %s\nHTML -> %s" % (args.json, args.html))


if __name__ == "__main__":
    main()
