#!/usr/bin/env python3
"""项目演示 Web 服务（只用 Python 标准库，不引入 Web 框架）。

浏览器负责选择/上传音频和展示结果；真正的检索仍调用 mirtool：
音频 -> MFCC -> k-means -> 高斯指纹 -> 对称 KL -> EMD。
"""
import argparse
import json
import atexit
import mimetypes
import os
import shutil
import tempfile
import threading
import uuid
from collections import OrderedDict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlparse

from mirtool.audio import TARGET_FS, write_wav
from mirtool.pipeline import (AUDIO_EXT, load_index_config, load_meta,
                              load_signatures, signature_from_audio)
from mirtool.search import rank

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
SIG_DIR = os.path.join(DATA_DIR, "sig")
SONGS_DIR = os.path.join(DATA_DIR, "songs")
CLIPS_DIR = os.path.join(DATA_DIR, "clips")
META_PATH = os.path.join(DATA_DIR, "meta.json")
EVAL_PATH = os.path.join(ROOT, "out", "evaluation.json")
UPLOAD_DIR = tempfile.mkdtemp(prefix="mir-project1-uploads-")
atexit.register(shutil.rmtree, UPLOAD_DIR, ignore_errors=True)
MAX_UPLOAD = 100 * 1024 * 1024
MAX_UPLOAD_CLIPS = 20
UPLOAD_CHUNK = 1024 * 1024


class State:
    def __init__(self):
        self.library = load_signatures(SIG_DIR)
        self.names = sorted(self.library)
        self.meta = load_meta(META_PATH)
        self.index_config = load_index_config(SIG_DIR)
        self.metrics = {}
        self.upload_clips = OrderedDict()
        self.upload_lock = threading.Lock()

        if os.path.exists(EVAL_PATH):
            with open(EVAL_PATH, encoding="utf-8") as f:
                self.metrics = json.load(f).get("overall", {})

    def song_json(self, name):
        m = self.meta.get(name, {})
        return {
            "name": name,
            "title": m.get("title", name),
            "artist": m.get("artist", ""),
            "family": m.get("family", ""),
            "audio": "/audio/library/%s.wav" % quote(name, safe=""),
        }

    def search_library(self, query, top=10):
        if query not in self.library:
            raise ValueError("曲库里没有这首歌")
        # 48 首规模直接线性扫描即可；这样替换歌曲并重建索引后不会读到旧距离缓存。
        pairs = rank(self.library[query], self.library, top=top, exclude=query)
        return self.format_results(query, pairs)

    def format_results(self, query, pairs, query_audio=None, is_upload=False):
        q = {
            "name": query, "title": query, "artist": "上传文件", "family": "未知（不参与排序）",
            "audio": query_audio,
        } if is_upload else self.song_json(query)
        results = []
        for name, distance in pairs:
            item = self.song_json(name)
            item["distance"] = float(distance)
            results.append(item)
        return {"query": q, "results": results}

    def _remember_upload_clip(self, token, clip):
        self.upload_clips[token] = clip
        self.upload_clips.move_to_end(token)
        while len(self.upload_clips) > MAX_UPLOAD_CLIPS:
            _, old_path = self.upload_clips.popitem(last=False)
            try:
                os.remove(old_path)
            except OSError:
                pass

    def search_upload_file(self, filename, source, token, top=10):
        # clip 必须和上传源文件使用不同路径；否则 WAV 上传成功后 finally 会把试听文件删掉。
        clip = os.path.join(UPLOAD_DIR, token + "-clip.wav")
        seconds = float(self.index_config["seconds"])
        k = int(self.index_config["k"])
        cmn = bool(self.index_config["cmn"])
        try:
            sig, segment = signature_from_audio(source, seconds=seconds, k=k, cmn=cmn)
            write_wav(clip, segment, TARGET_FS)
            pairs = rank(sig, self.library, top=top)
            self._remember_upload_clip(token, clip)
            name = os.path.splitext(os.path.basename(filename))[0]
            return self.format_results(name, pairs, "/audio/upload/%s.wav" % token,
                                       is_upload=True)
        except Exception:
            try:
                os.remove(clip)
            except OSError:
                pass
            raise
        finally:
            try:
                os.remove(source)
            except OSError:
                pass


STATE = State()


INDEX_HTML = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>相似歌曲检索系统</title>
<style>
:root{--bg:#f4f6f9;--surface:#fff;--ink:#172033;--muted:#697386;--line:#e1e5eb;
--blue:#2563eb;--blue2:#e9f0ff;--good:#16794b;--goodbg:#e8f7ef;--warn:#9a6700}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 -apple-system,
BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}header{background:#14213d;color:white;padding:26px 20px}
header>div,main{max-width:1080px;margin:auto}h1{font-size:25px;margin:0 0 3px}header p{margin:0;color:#cbd5e1}
main{padding:22px 20px 60px}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:18px}
.metric,.panel{background:var(--surface);border:1px solid var(--line);border-radius:11px}.metric{padding:14px 16px}
.metric b{font-size:22px;display:block}.metric span{font-size:12px;color:var(--muted)}.panel{padding:18px;margin-bottom:16px}
h2{font-size:17px;margin:0 0 13px}.controls{display:flex;gap:9px;align-items:center;flex-wrap:wrap}
select,input[type=file]{min-height:39px;border:1px solid #cbd1da;border-radius:7px;background:#fff;padding:7px;min-width:240px}
button{min-height:39px;border:0;border-radius:7px;background:var(--blue);color:#fff;padding:8px 18px;font-weight:650;cursor:pointer}
button:hover{filter:brightness(.94)}button:disabled{opacity:.55;cursor:wait}.or{color:var(--muted);font-size:12px;padding:0 3px}
.help{font-size:12px;color:var(--muted);margin-top:9px}.status{padding:12px;border-radius:7px;background:var(--blue2);color:#244477}
.error{background:#fff0ef;color:#9f1c14}.query{display:flex;align-items:center;justify-content:space-between;gap:16px;
background:#f8fafc;border:1px solid var(--line);padding:12px 14px;border-radius:8px;margin-bottom:12px}.query b{font-size:16px}
audio{height:32px;max-width:280px}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;min-width:780px}
th,td{border-bottom:1px solid var(--line);padding:9px;text-align:left}th{font-size:12px;color:var(--muted);background:#f7f8fa}
tr.same{background:var(--goodbg)}.rank{font-weight:700;color:var(--muted)}.family{background:#eef1f5;border-radius:4px;padding:2px 6px;
white-space:nowrap}.same .family{background:#cfeddc;color:var(--good)}.distance{font-variant-numeric:tabular-nums}
.bar{display:inline-block;vertical-align:middle;width:100px;height:7px;background:#e7e9ed;border-radius:4px;overflow:hidden;margin-left:7px}
.bar i{display:block;height:100%;background:var(--blue);border-radius:4px}.method{display:grid;grid-template-columns:repeat(5,1fr);gap:8px}
.step{border:1px solid var(--line);border-radius:8px;padding:11px;text-align:center}.step b{display:block;color:var(--blue);font-size:16px}
.step span{font-size:12px;color:var(--muted)}.arrow{display:none}.foot{font-size:12px;color:var(--muted)}
@media(max-width:760px){.metrics{grid-template-columns:repeat(2,1fr)}.method{grid-template-columns:1fr}.query{align-items:flex-start;flex-direction:column}}
</style></head><body>
<header><div><h1>相似歌曲检索系统</h1><p>不用歌名和歌手，仅根据音频波形寻找音色相似的歌曲</p></div></header>
<main>
<section id="metrics" class="metrics"></section>
<section class="panel"><h2>开始检索</h2><div class="controls">
<select id="song"><option>正在加载曲库…</option></select><button id="search">检索相似歌曲</button>
<span class="or">或者</span><input id="file" type="file" accept="audio/*,.mp3,.wav,.flac,.m4a,.aac,.ogg,.wma"><button id="upload">上传并检索</button>
</div><div class="help">上传文件只用于本次检索，不进入曲库；系统截取中间 30 秒。第一次上传分析约需数秒。</div></section>
<div id="status" class="status">请选择一首演示歌曲，或上传自己的音频。</div>
<section id="result" class="panel" style="display:none"></section>
<section class="panel"><h2>系统原理（答辩时按这 5 步讲）</h2><div class="method">
<div class="step"><b>① 截取</b><span id="step-cut">中间 30 秒<br>16 kHz 单声道</span></div>
<div class="step"><b>② MFCC</b><span id="step-mfcc">每 10 ms 一帧<br>3000 × 20 维</span></div>
<div class="step"><b>③ k-means</b><span id="step-k">3000 帧聚成<br>16 个音色类</span></div>
<div class="step"><b>④ KL + EMD</b><span>类间对称 KL<br>整曲推土机距离</span></div>
<div class="step"><b>⑤ 排序</b><span>线性扫描曲库<br>距离越小越相似</span></div>
</div></section>
<div class="foot"><span id="library-note">演示库信息加载中…</span><span id="evaluation-link"> 完整评估报告：<a href="/evaluation">打开 evaluation.html</a></span></div>
</main>
<script>
const $=s=>document.querySelector(s);let songs=[],info={};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=v=>(100*v).toFixed(1)+'%';
async function init(){try{const x=await fetch('/api/info').then(r=>r.json());info=x;songs=x.songs;
$('#song').innerHTML=songs.map(s=>`<option value="${esc(s.name)}">${esc(s.title)} — ${esc(s.artist)} [${esc(s.family)}]</option>`).join('');
const m=x.metrics||{},cfg=x.index||{};$('#metrics').innerHTML=[['Top-1 准确率',m.top1_accuracy],['Precision@5',m.precision_at_k],['Recall@5',m.recall_at_k],['mAP',m.map]].map(([n,v])=>`<div class="metric"><b>${v==null?'—':pct(v)}</b><span>${n}</span></div>`).join('');
const frames=Math.round((cfg.seconds||30)*(cfg.sample_rate||16000)/160);
$('#step-cut').innerHTML=`中间 ${cfg.seconds||30} 秒<br>${(cfg.sample_rate||16000)/1000} kHz 单声道`;
$('#step-mfcc').innerHTML=`每 10 ms 一帧<br>${frames} × ${cfg.mfcc_dim||20} 维`;
$('#step-k').innerHTML=`${frames} 帧聚成<br>${cfg.k||16} 个音色类`;
$('#library-note').textContent=`演示库：${songs.length} 首可自由使用的合成歌曲，${x.family_count||0} 个音色家族。家族标签只用于评估和结果着色，不参与检索。`;
$('#evaluation-link').style.display=x.evaluation_available?'inline':'none';
}catch(e){showError(e)}}
function busy(on,text){$('#search').disabled=on;$('#upload').disabled=on;if(on){$('#status').style.display='block';$('#status').className='status';$('#status').textContent=text}}
function showError(e){$('#status').style.display='block';$('#status').className='status error';$('#status').textContent='错误：'+e.message;busy(false)}
async function jsonOrError(r){const x=await r.json();if(!r.ok)throw new Error(x.error||'请求失败');return x}
$('#search').onclick=async()=>{busy(true,'正在计算并排序…');try{const q=encodeURIComponent($('#song').value);render(await fetch('/api/search?query='+q).then(jsonOrError))}catch(e){showError(e)}finally{busy(false)}};
$('#upload').onclick=async()=>{const f=$('#file').files[0];if(!f)return showError(new Error('请先选择音频文件'));
busy(true,'正在解码音频、提取 MFCC、聚类并计算 EMD，请稍候…');try{render(await fetch('/api/search-upload?filename='+encodeURIComponent(f.name),{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:f}).then(jsonOrError))}catch(e){showError(e)}finally{busy(false)}};
function render(x){$('#status').style.display='none';const q=x.query,rs=x.results,max=Math.max(...rs.map(r=>r.distance)),min=Math.min(...rs.map(r=>r.distance));
const denom=Math.max(max-min,1e-9);let h=`<h2>检索结果</h2><div class="query"><div><b>${esc(q.title)}</b><br><span>${esc(q.artist)} · ${esc(q.family||'未知家族')}</span></div><audio controls src="${esc(q.audio)}"></audio></div>`;
h+=`<div class="table-wrap"><table><thead><tr><th>排名</th><th>EMD（越小越像）</th><th>歌曲</th><th>艺术家</th><th>音色家族</th><th>试听</th></tr></thead><tbody>`;
rs.forEach((r,i)=>{const same=q.family&&q.family!=='未知（不参与排序）'&&r.family===q.family;const w=100*(max-r.distance)/denom;
h+=`<tr class="${same?'same':''}"><td class="rank">${i+1}</td><td class="distance">${r.distance.toFixed(2)}<span class="bar" title="仅表示本次结果内的相对距离"><i style="width:${Math.max(3,w)}%"></i></span></td><td><b>${esc(r.title)}</b></td><td>${esc(r.artist)}</td><td><span class="family">${esc(r.family)}</span></td><td><audio controls preload="none" src="${esc(r.audio)}"></audio></td></tr>`});
h+='</tbody></table></div><div class="help">绿色行表示与查询歌曲属于同一音色家族，仅用于验证效果；算法计算距离时没有读取这些标签。</div>';$('#result').innerHTML=h;$('#result').style.display='block';$('#result').scrollIntoView({behavior:'smooth',block:'start'})}
init();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "MIRProject/1.0"
    timeout = 60

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args), flush=True)

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, body, content_type, cache=False):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=3600" if cache else "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path, content_type=None):
        if not os.path.isfile(path):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        with open(path, "rb") as f:
            body = f.read()
        self.send_bytes(body, content_type or mimetypes.guess_type(path)[0] or "application/octet-stream", True)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            self.send_bytes(INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
        elif u.path == "/health":
            self.send_json({"status": "ok", "songs": len(STATE.names)})
        elif u.path == "/api/info":
            families = sorted({STATE.meta.get(n, {}).get("family", "")
                               for n in STATE.names} - {""})
            self.send_json({"songs": [STATE.song_json(n) for n in STATE.names],
                            "metrics": STATE.metrics,
                            "index": STATE.index_config,
                            "family_count": len(families),
                            "evaluation_available": os.path.isfile(
                                os.path.join(ROOT, "out", "evaluation.html"))})
        elif u.path == "/api/search":
            try:
                query = parse_qs(u.query).get("query", [""])[0]
                self.send_json(STATE.search_library(query))
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
        elif u.path == "/evaluation":
            self.send_file(os.path.join(ROOT, "out", "evaluation.html"), "text/html; charset=utf-8")
        elif u.path.startswith("/audio/library/"):
            name = unquote(u.path[len("/audio/library/"):])
            if name.endswith(".wav"):
                name = name[:-4]
            # 只能从已载入的白名单曲名中取文件，防止 ../ 路径穿越
            if name not in STATE.library:
                self.send_error(HTTPStatus.NOT_FOUND)
            else:
                self.send_file(os.path.join(CLIPS_DIR, name + ".wav"), "audio/wav")
        elif u.path.startswith("/audio/upload/"):
            token = os.path.basename(u.path)[0:-4] if u.path.endswith(".wav") else os.path.basename(u.path)
            path = STATE.upload_clips.get(token)
            self.send_file(path, "audio/wav") if path else self.send_error(HTTPStatus.NOT_FOUND)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/api/search-upload":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        source = None
        acquired = False
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                raise ValueError("上传内容为空")
            if length > MAX_UPLOAD:
                raise ValueError("文件超过 100 MB 限制")
            filename = parse_qs(u.query).get("filename", ["upload.wav"])[0]
            ext = os.path.splitext(filename)[1].lower()
            if ext not in AUDIO_EXT:
                supported = "、".join(x[1:].upper() for x in AUDIO_EXT)
                raise ValueError("不支持 %s；请上传 %s" % (ext or "无扩展名文件", supported))

            token = uuid.uuid4().hex
            source = os.path.join(UPLOAD_DIR, token + "-source" + ext)
            remaining = length
            with open(source, "wb") as f:
                while remaining:
                    chunk = self.rfile.read(min(UPLOAD_CHUNK, remaining))
                    if not chunk:
                        raise ValueError("上传中断，收到的数据少于 Content-Length")
                    f.write(chunk)
                    remaining -= len(chunk)

            acquired = STATE.upload_lock.acquire(blocking=False)
            if not acquired:
                self.send_json({"error": "已有一个音频正在分析，请稍后重试"}, 503)
                return
            result = STATE.search_upload_file(filename, source, token)
            source = None  # search_upload_file 已负责删除
            self.send_json(result)
        except (ValueError, RuntimeError) as e:
            self.send_json({"error": str(e)}, 400)
        except Exception as e:
            print("上传处理失败: %r" % e, flush=True)
            self.send_json({"error": "服务器处理音频失败，请查看容器日志"}, 500)
        finally:
            if source:
                try:
                    os.remove(source)
                except OSError:
                    pass
            if acquired:
                STATE.upload_lock.release()


def main():
    p = argparse.ArgumentParser(description="相似歌曲检索 Web 演示")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8088")))
    args = p.parse_args()
    if not STATE.library:
        raise SystemExit("特征库为空，请先运行 scripts/build_index.py")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("相似歌曲检索系统已启动：http://localhost:%d（%d 首歌曲）" %
          (args.port, len(STATE.library)), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
