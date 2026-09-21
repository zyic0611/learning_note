"""把检索结果写成带播放器的 HTML，方便直接试听对比。"""
import html
import os

from .audio import write_wav, load_audio, center_segment, TARGET_FS
from .pipeline import song_files


def _meta_of(meta, name):
    return meta.get(name, {}) if isinstance(meta, dict) else {}


def ensure_clip(name, songs_dir, clip_dir, seconds=30.0):
    """确保 clip_dir/<name>.wav 存在（HTML 播放器要用中间 30 秒的片段）。"""
    dst = os.path.join(clip_dir, name + ".wav")
    if os.path.exists(dst):
        return dst
    src = _find_song(songs_dir, name)
    if src is None:
        return None
    x, fs = load_audio(src, TARGET_FS, max_seconds=seconds)
    write_wav(dst, center_segment(x, fs, seconds), TARGET_FS)
    return dst


def _find_song(songs_dir, name):
    return song_files(songs_dir).get(name) if songs_dir else None


def write_html(out_path, query_name, results, meta=None, clip_dir=None,
               songs_dir=None, top=10, seconds=30.0, cmn=False, k=16):
    """results: [(名字, EMD), ...]，已按距离升序。"""
    meta = meta or {}
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    if clip_dir:
        os.makedirs(clip_dir, exist_ok=True)
        ensure_clip(query_name, songs_dir, clip_dir, seconds)
        for name, _ in results:
            ensure_clip(name, songs_dir, clip_dir, seconds)

    q_family = _meta_of(meta, query_name).get("family")
    max_emd = max([e for _, e in results] + [1e-9])
    rel_clip = os.path.relpath(clip_dir, os.path.dirname(os.path.abspath(out_path))) if clip_dir else ""

    same_hits = sum(1 for n, _ in results[:top]
                    if q_family and _meta_of(meta, n).get("family") == q_family)

    lines = []
    a = lines.append
    a("<!DOCTYPE html>")
    a('<html lang="zh"><head><meta charset="utf-8">')
    a("<title>相似歌曲检索结果 - %s</title>" % html.escape(query_name))
    a("""<style>
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
     margin:32px auto;max-width:960px;color:#1a1a1a;background:#fafafa}
h1{font-size:20px;margin:0 0 4px}
.sub{color:#666;font-size:13px;margin-bottom:20px}
.card{background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:16px 20px;margin-bottom:20px}
table{border-collapse:collapse;width:100%;font-size:14px;background:#fff}
th,td{padding:9px 10px;border-bottom:1px solid #eee;text-align:left}
th{background:#f5f5f5;font-weight:600;font-size:13px;color:#444}
tr.hit{background:#eefaf0}
tr.query{background:#eef4ff;font-weight:600}
.bar{background:#e8e8e8;border-radius:4px;height:8px;width:120px;overflow:hidden;display:inline-block;vertical-align:middle}
.bar>i{display:block;height:100%;background:#3b82f6}
.emd{font-variant-numeric:tabular-nums;color:#333}
audio{height:30px;vertical-align:middle}
.tag{font-size:11px;background:#eee;border-radius:4px;padding:1px 6px;color:#555}
code{background:#f0f0f0;padding:1px 5px;border-radius:3px;font-size:12px}
</style></head><body>""")
    a("<h1>相似歌曲检索结果</h1>")
    a('<div class="sub">查询歌曲：<b>%s</b>%s ｜ 特征：%d 维 MFCC × %d 类高斯，对称 KL + EMD%s ｜ 共比对 %d 首</div>'
      % (html.escape(query_name),
         "（音色家族：%s）" % html.escape(q_family) if q_family else "",
         20, k, "，含倒谱均值归一化" if cmn else "",
         len(results)))

    a('<div class="card"><b>查询片段</b>（中间 %d 秒）<br><br>' % int(seconds))
    a('<audio controls src="%s/%s.wav"></audio>' % (rel_clip, html.escape(query_name)))
    a("</div>")

    a('<div class="card">')
    a("<table><thead><tr><th>排名</th><th>EMD（越小越像）</th><th>相似度</th>"
      "<th>标题</th><th>艺术家 / 家族</th><th>试听</th></tr></thead><tbody>")
    for i, (name, e) in enumerate(results[:top], 1):
        m = _meta_of(meta, name)
        fam = m.get("family", "")
        cls = "query" if name == query_name else ("hit" if (q_family and fam == q_family) else "")
        width = max(2.0, 100.0 * (1.0 - e / max_emd))
        title = m.get("title", name)
        artist = m.get("artist", fam) or "—"
        a('<tr class="%s"><td>%d</td><td class="emd">%.2f</td>'
          '<td><span class="bar"><i style="width:%.0f%%"></i></span></td>'
          '<td>%s</td><td>%s %s</td>'
          '<td><audio controls src="%s/%s.wav"></audio></td></tr>'
          % (cls, i, e, width, html.escape(title), html.escape(str(artist)),
             '<span class="tag">同家族</span>' if (q_family and fam == q_family and name != query_name) else "",
             rel_clip, html.escape(name)))
    a("</tbody></table></div>")

    if q_family:
        a('<div class="card">Top-%d 里有 <b>%d</b> 首和查询歌曲属于同一音色家族（“%s”）。'
          '绿色行表示命中同一家族。</div>' % (top, same_hits, html.escape(q_family)))

    a('<div class="sub">提示：从库内选择查询歌曲时，结果默认排除歌曲自身；EMD 越小表示音色分布越接近。</div>')
    a("</body></html>")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_path
