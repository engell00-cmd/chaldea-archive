#!/usr/bin/env python3
"""칼데아 기록 보관소 사이트 빌드.

logs/ 의 정리된 로그(HTML)와 data/ 의 PL 공개 데이터로 _site/ 를 만든다.
  _site/index.html    칼데아스 관측실 (특이점 지도)
  _site/archive.html  기록 보관소 (로그 목록)
  _site/board.html    마슈의 인물 관계도
  _site/logs/*.html   칼데아 테마를 입힌 로그
GitHub Actions 가 logs/ 나 data/ 가 바뀔 때마다 자동으로 실행한다.
⚠ 이 저장소는 공개다. GM 전용 정보는 절대 data/ 나 logs/ 에 넣지 않는다.
"""
import base64, datetime, html, json, os, re, shutil, subprocess, sys
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, "build")
OUT = os.path.join(ROOT, "_site")
sys.path.insert(0, B)
import chaldea_theme as CT  # noqa: E402

def rd(p, mode="r"):
    with open(p, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        return f.read()
def jl(name):
    return json.loads(rd(os.path.join(ROOT, "data", name)))

cat = jl("catalog.json"); rel = jl("relations.json"); tokens = jl("tokens.json"); atlas = jl("atlas.json")
scenes = jl("scenes.json") if os.path.exists(os.path.join(ROOT, "data", "scenes.json")) else {}
emblem = "data:image/webp;base64," + base64.b64encode(rd(os.path.join(B, "emblem.webp"), "rb")).decode()

def git_date(path):
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", path], cwd=ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
        return out
    except Exception:
        return ""

# ---- 로그 읽기 ----
logs = []
for fn in sorted(os.listdir(os.path.join(ROOT, "logs"))):
    if not re.search(r"\.html?$", fn, re.I):
        continue
    if any(k in fn for k in cat.get("exclude_keywords", [])):
        print("건너뜀(제외 키워드):", fn); continue
    p = os.path.join(ROOT, "logs", fn)
    src = rd(p)
    m = re.search(r'<h1 class="log-title">(.*?)</h1>', src, re.S)
    if not m:
        print("건너뜀(정리된 로그 형식 아님):", fn); continue
    title = html.unescape(re.sub("<[^>]+>", "", m.group(1))).strip()
    meta = [html.unescape(x) for x in re.findall(r'<div class="log-meta">(.*?)</div>', src, re.S)[:1]]
    meta = re.findall(r"<span>(.*?)</span>", meta[0]) if meta else []
    cast = []
    tk = dict(re.findall(r'\.(tk\d+)\{background-image:url\("(data:image/webp;base64,[A-Za-z0-9+/=]+)"\)\}', src))
    for cls, nm in re.findall(r'<span style="--h:\d+">(?:<i class="tk (tk\d+)"></i>)?([^<]+)</span>', src):
        nm = html.unescape(nm).strip()
        if nm.startswith("GM") or "「" in nm or "【" in nm or nm.endswith(".") or len(nm) > 20:
            continue
        cast.append((nm, tk.get(cls)))
    group = next((r["group"] for r in cat["rules"] if any(k in fn or k in title for k in (r["match"] if isinstance(r["match"], list) else [r["match"]]))), "기타")
    out_name = re.sub(r"\.htm$|\.HTML$|\.HTM$", ".html", fn)
    logs.append(dict(fn=fn, out=out_name, title=title, meta=meta, cast=cast, group=group, date=git_date(p), src=src))

# ---- 관계도 토큰: 로그에 나온 토큰으로 빈 카드를 자동으로 채운다 ----
idx = {}
for n in rel["nodes"]:
    for k in [n["name"], n.get("short") or n["name"]] + n.get("aliases", []):
        idx[k] = n
for lg in logs:
    for nm, uri in lg["cast"]:
        n = idx.get(nm)
        if n and uri and not n.get("tok"):
            n["tok"] = "auto:" + n["id"]; tokens[n["tok"]] = uri.split(",", 1)[1]
            print("토큰 자동 추가:", n["name"], "←", lg["fn"])

mini = dict(nodes=[dict(id=n["id"], names=[n["name"], n.get("short") or n["name"]] + n.get("aliases", [])) for n in rel["nodes"]],
            edges=[dict(a=e["a"], b=e["b"], label=e.get("label") or "██████", kind=e["kind"]) for e in rel["edges"]])

NAV_LINKS = [("index.html", "칼데아스 관측실"), ("archive.html", "기록 보관소"), ("board.html", "인물 관계도")]
def navlinks(cur, prefix=""):
    return "".join(f'<a href="{prefix}{h}"{" aria-current=page" if h == cur else ""}>{t}</a>' for h, t in NAV_LINKS)

if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(os.path.join(OUT, "logs"))

# ---- 로그 페이지 ----
for lg in logs:
    page = CT.themed(lg["src"], scenes, atlas_href="../index.html", board_href="../board.html", rel_json=json.dumps(mini, ensure_ascii=False),
                     extra_nav='<a class="cx-atlas" href="../archive.html">기록 보관소</a>')
    with open(os.path.join(OUT, "logs", lg["out"]), "w", encoding="utf-8") as f:
        f.write(page)

# ---- 관측실 (index) ----
items = []
for it in atlas["items"]:
    it = dict(it)
    if not it.get("redacted"):
        keys = cat.get("singularity_logs", {}).get(it["id"], [])
        it["logs"] = [(lg["title"], "logs/" + quote(lg["out"])) for lg in logs if any(k in lg["fn"] or k in lg["title"] for k in keys)]
        it.setdefault("pl", []); it.setdefault("map", "")
    items.append(it)
T = rd(os.path.join(B, "atlas_template.html"))
STL = {"cleared": "수복 완료", "active": "진행 중", "unobserved": "미관측"}
lis = ""
for it in items:
    if it.get("redacted"):
        lis += f'<li><button type="button"><span class="no">{html.escape(it["no"])}</span><span class="tt"><b><span class="bar">■■■■■■■■</span></b><span>관측 불가</span></span><span class="st redacted">미관측</span></button></li>'
    else:
        lis += f'<li><button type="button"><span class="no">{html.escape(it["no"])}</span><span class="tt"><b>{html.escape(it["title"])}</b><span>{html.escape(it["year"])} · {html.escape(it["place"])}</span></span><span class="st {it["status"]}">{STL[it["status"]]}</span></button></li>'
import math
def lens(n=16, r=186, size=13):
    o = []
    for i in range(n):
        a = 2 * math.pi * i / n; cx, cy = 200 + r * math.cos(a), 200 + r * math.sin(a)
        pts = " ".join(f"{cx + size * math.cos(math.pi / 3 * k + a):.1f},{cy + size * math.sin(math.pi / 3 * k + a):.1f}" for k in range(6))
        o.append(f'<polygon points="{pts}" stroke-width=".9"/>')
    return "".join(o) + '<circle cx="200" cy="200" r="186" stroke-width=".4"/><circle cx="200" cy="200" r="170" stroke-width=".5" stroke-dasharray="2 6"/>'
h = T.replace("__LISTHTML__", lis).replace("__TITLE__", "칼데아스 관측실").replace("__VERCLS__", "").replace("__VER__", "PL 공개용")
h = h.replace("__SRC__", "근거: 칼데아 공개 기록 · 세션 로그").replace("__FALLBACK__", rd(os.path.join(B, "atlas_fallback.txt")).strip())
h = h.replace("__BOARD__", "board.html").replace("__EMBLEM__", emblem).replace("__LENS__", lens()).replace("__LAND__", rd(os.path.join(B, "land1.b64")).strip())
h = h.replace("__DATA__", json.dumps(dict(ver="pl", items=items), ensure_ascii=False).replace("</", "<\\/"))
h = h.replace('<span>Chaldeas observation</span>', '<nav class="snav">' + navlinks("index.html") + '</nav>')
h = h.replace("</style>", ".snav{display:flex;gap:4px;flex-wrap:wrap}.snav a{color:var(--muted);text-decoration:none;padding:3px 8px;border:1px solid transparent;border-radius:2px}.snav a:hover{color:var(--fg);border-color:var(--line)}.snav a[aria-current]{color:var(--accent);border-color:var(--accent)}</style>", 1)
with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
    f.write(h)

# ---- 관계도 ----
T = rd(os.path.join(B, "board_template.html"))
used = {n["tok"] for n in rel["nodes"] if n.get("tok")}
data = dict(ver="pl", groups=rel["groups"], nodes=rel["nodes"], edges=rel["edges"],
            tokens={k: "data:image/webp;base64," + v for k, v in tokens.items() if k in used}, src="근거: 세션 로그 · 칼데아 공개 기록")
for n in data["nodes"]:
    if n.get("tok") and n["tok"] not in data["tokens"]:
        n["tok"] = None
h = T.replace("__TITLE__", "인물 관계도").replace("__ATLAS__", "index.html").replace("__VERCLS__", "pl").replace("__VERLABEL__", "PL 공개용")
h = h.replace("__LEGEND_SECRET__", '<div class="k"><b style="border-color:var(--noir);border-top-style:dashed"></b>아직 밝혀지지 않음</div>')
h = h.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
h = h.replace('<a class="btn" href="index.html" style="text-decoration:none">칼데아스 관측실 →</a>',
              '<a class="btn" href="index.html" style="text-decoration:none">칼데아스 관측실</a><a class="btn" href="archive.html" style="text-decoration:none">기록 보관소</a>')
with open(os.path.join(OUT, "board.html"), "w", encoding="utf-8") as f:
    f.write(h)

# ---- 기록 보관소 ----
order = cat.get("groups", [])
groups = sorted({lg["group"] for lg in logs}, key=lambda g: (order.index(g) if g in order else 99, g))
lst = ""
for g in groups:
    cards = ""
    gl = sorted([lg for lg in logs if lg["group"] == g], key=lambda x: (x["date"] or "9999", x["fn"]), reverse=False)
    for lg in gl:
        names = [c[0] for c in lg["cast"]]
        s = " ".join([lg["title"], g] + names).lower()
        rid = "REC-" + __import__("hashlib").sha1(lg["title"].encode("utf-8")).hexdigest()[:6].upper()
        cards += (f'<a class="card" href="logs/{quote(lg["out"])}" data-s="{html.escape(s)}"><span class="id">{rid}{" · " + lg["date"] if lg["date"] else ""}</span>'
                  f'<b>{html.escape(lg["title"])}</b><span class="meta">{html.escape(" · ".join(lg["meta"]))}</span>'
                  f'<div class="cast">{html.escape(", ".join(names))}</div></a>')
    lst += f'<section><h2>{html.escape(g)}</h2><div class="grid">{cards}</div></section>'
NAVCSS = """.band{display:flex;align-items:center;gap:10px 16px;flex-wrap:wrap;padding:10px 20px;border-bottom:1px solid var(--line);background:linear-gradient(90deg,var(--accent-soft),transparent 70%);font:600 11px/1.4 var(--f-label);letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
.band .org{color:var(--accent)}.band .emb{width:18px;height:18px;background:var(--accent);-webkit-mask:var(--cx-emblem) center/contain no-repeat;mask:var(--cx-emblem) center/contain no-repeat}
.snav{display:flex;gap:4px;flex-wrap:wrap}.snav a{color:var(--muted);text-decoration:none;padding:3px 8px;border:1px solid transparent;border-radius:2px}.snav a:hover{color:var(--fg);border-color:var(--line)}.snav a[aria-current]{color:var(--accent);border-color:var(--accent)}
.light{margin-left:auto;display:inline-flex;align-items:center;gap:8px;background:none;border:1px solid var(--line);border-radius:2px;padding:4px 8px 4px 10px;color:var(--muted);font:inherit;cursor:pointer}
.light .sw{position:relative;width:26px;height:14px;border-radius:2px;background:var(--accent-soft);border:1px solid var(--line)}
.light .sw::after{content:"";position:absolute;top:1px;left:1px;width:10px;height:10px;border-radius:1px;background:var(--muted);transition:transform .2s}
.light[aria-pressed="true"] .sw::after{transform:translateX(12px);background:var(--accent)}"""
NAV = '<div class="band"><i class="emb"></i><span class="org">Chaldea · 기록 보관소</span><nav class="snav">' + navlinks("archive.html") + '</nav><button class="light" type="button" aria-pressed="false"><span class="lb">조명</span><span class="sw"></span></button></div>'
NAVJS = """<script>(function(){var b=document.querySelector('.light'),r=document.documentElement,K='cx-lights';function d(){return matchMedia('(prefers-color-scheme: dark)').matches}function on(){var t=r.getAttribute('data-theme');return t?t==='light':!d()}function L(){b.setAttribute('aria-pressed',on()?'true':'false');b.querySelector('.lb').textContent=on()?'조명 ON':'조명 OFF'}function s(v){r.setAttribute('data-theme',v?'light':'dark');L();try{localStorage.setItem(K,v?'on':'off')}catch(e){}}var v=null;try{v=localStorage.getItem(K)}catch(e){}if(v==='on'||v==='off')s(v==='on');else L();b.onclick=function(){s(!on())}})();</script>"""
h = rd(os.path.join(B, "archive_template.html")).replace("__EMBLEM__", emblem).replace("__NAVCSS__", NAVCSS).replace("__NAV__", NAV).replace("__NAVJS__", NAVJS)
h = h.replace("__LIST__", lst or '<p class="empty">아직 올라온 기록이 없네.</p>').replace("__UPDATED__", "갱신 " + datetime.date.today().isoformat())
with open(os.path.join(OUT, "archive.html"), "w", encoding="utf-8") as f:
    f.write(h)
open(os.path.join(OUT, ".nojekyll"), "w").close()
print(f"완료: 로그 {len(logs)}편 · 특이점 {len(items)} · 인물 {len(rel['nodes'])}")
