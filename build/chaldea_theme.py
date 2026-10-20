#!/usr/bin/env python3
"""포켓몬 그랜드 오더 로그(HTML)에 칼데아 테마를 입힌다.

사용법:
  python chaldea_theme.py 입력.html [출력.html] [--scenes scenes.json]
  - 출력 경로를 생략하면 '입력 (칼데아).html'로 저장한다.
  - 이미 테마가 입혀진 파일에 다시 돌려도 이전 테마를 걷어내고 새로 입힌다.
  - scenes.json: {"칼데아": "https://.../chaldea.webp", "기본": "..."} 형식.
    로그 안의 「배경」 「장면명」 줄을 만나면 그 장면 이미지로 배경이 바뀐다.
"""
import base64, hashlib, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
B, E = "<!--CX:BEGIN-->", "<!--CX:END-->"

FONTS = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;600&display=swap">'

def lens_ring(n=14, r=172, size=15):
    out = []
    import math
    for i in range(n):
        a = 2 * math.pi * i / n
        cx, cy = 200 + r * math.cos(a), 200 + r * math.sin(a)
        pts = " ".join(f"{cx + size*math.cos(math.pi/3*k + a):.1f},{cy + size*math.sin(math.pi/3*k + a):.1f}" for k in range(6))
        out.append(f'<polygon points="{pts}"/>')
    return "".join(out)

GLOBE_INNER = (
    '<canvas class="cx-globe-cv"></canvas>'
    '<svg class="cx-globe" viewBox="0 0 400 400" fill="none" stroke="currentColor" aria-hidden="true">'
    '<circle cx="200" cy="200" r="150" stroke-width=".6" stroke-dasharray="2 6"/>'
    '<ellipse cx="200" cy="200" rx="188" ry="46" stroke-width=".7" transform="rotate(-18 200 200)"/>'
    f'<g class="lens" stroke-width=".9">{lens_ring()}<circle cx="200" cy="200" r="172" stroke-width=".4"/></g>'
    '</svg>'
)
GLOBE = '<div class="cx-globe-wrap">' + GLOBE_INNER + '</div>'
HERO = '<div class="cx-hero" aria-hidden="true">' + GLOBE_INNER + '</div>'

MOUNTAINS = (
    '<svg class="cx-mtn" viewBox="0 0 1440 320" preserveAspectRatio="none" aria-hidden="true">'
    '<path class="r1" d="M0 220 L120 150 L210 190 L330 90 L430 170 L540 120 L660 200 L790 70 L900 160 L1010 110 L1130 180 L1250 100 L1360 170 L1440 140 L1440 320 L0 320Z"/>'
    '<path class="sn" d="M330 90 L300 115 L322 110 L340 122 L355 108 Z M790 70 L755 104 L782 96 L800 112 L820 96 Z M1250 100 L1222 126 L1246 120 L1262 132 L1276 118 Z"/>'
    '<path class="r2" d="M0 270 L150 210 L260 250 L380 180 L500 240 L640 190 L760 260 L880 200 L1000 250 L1120 195 L1260 245 L1440 205 L1440 320 L0 320Z"/>'
    '<path class="sn" d="M380 180 L356 198 L378 194 L394 204 L404 192 Z M1120 195 L1098 212 L1118 208 L1132 218 L1142 206 Z"/>'
    '</svg>'
)

BG = (f'<div id="cx-bg" aria-hidden="true"><div class="cx-art"><div class="cx-glow"></div><div class="cx-grid"></div>'
      f'{GLOBE}<div class="cx-snowfall"></div>{MOUNTAINS}</div><div class="cx-photo"></div><div class="cx-veil"></div></div><div id="cx-lights"></div>')

def strip_old(s):
    return re.sub(re.escape(B) + r".*?" + re.escape(E), "", s, flags=re.S)

def wrap(x):
    return B + x + E

def themed(src, scenes, atlas_href='칼데아스 관측실 (PL 공개용).html', board_href='관계도 (PL 공개용).html', rel_json=None, extra_nav=''):
    s = strip_old(src)
    css = open(os.path.join(HERE, "theme.css"), encoding="utf-8").read()
    land = open(os.path.join(HERE, "land.b64"), encoding="ascii").read().strip()
    rp = os.path.join(HERE, "rel_pl.json")
    rel = rel_json if rel_json is not None else (open(rp, encoding="utf-8").read().strip() if os.path.exists(rp) else "null")
    ep = os.path.join(HERE, "emblem.webp")
    emblem = ("data:image/webp;base64," + base64.b64encode(open(ep, "rb").read()).decode()) if os.path.exists(ep) else ""
    css = ':root{--cx-emblem:url("%s")}' % emblem + css if emblem else css + ".cx-emblem{display:none}"
    fb = os.path.join(HERE, "hero_fallback.txt")
    if os.path.exists(fb): css = ':root{--cx-hero-fb:url("%s")}' % open(fb).read().strip() + css
    js = open(os.path.join(HERE, "theme.js"), encoding="utf-8").read()
    m = re.search(r'<h1 class="log-title">(.*?)</h1>', s, re.S)
    title = html.unescape(re.sub("<[^>]+>", "", m.group(1))).strip() if m else "SESSION RECORD"
    rid = "REC-" + hashlib.sha1(title.encode("utf-8")).hexdigest()[:6].upper()

    head = wrap(FONTS + "<style>" + css + "</style>")
    band = wrap(
        '<div class="cx-band"><i class="cx-emblem"></i><span class="cx-org">Chaldea · Finis Chaldea</span>'
        f'<span class="cx-id">{rid}</span><span>Record Archive</span>'
        '<span class="cx-stat"><i></i>Archived</span>' + extra_nav + '<a class="cx-atlas" href="' + html.escape(atlas_href) + '">칼데아스 관측실 →</a>'
        '<button class="cx-light" type="button" aria-pressed="false" title="관제실 조명 켜기/끄기"><span class="lb">조명</span><span class="sw"></span></button></div>')
    trow_open = wrap('<div class="cx-titlerow"><i class="cx-emblem"></i>' + HERO + '<div style="min-width:0"><p class="cx-kicker">인리계속보장기관 · 세션 기록</p>')
    trow_close = wrap('</div></div>')
    foot = wrap(f'<footer class="cx-foot"><span><i class="cx-emblem"></i>{html.escape(rid)} · End of record</span><span>Chaldea Security Organization</span></footer>')
    script = wrap("<script>window.CX_SCENES=" + json.dumps(scenes, ensure_ascii=False) + ";window.CX_LAND='" + land + "';window.CX_REL=" + rel.replace("</", "<\\/") + ";window.CX_BOARD=" + json.dumps(board_href, ensure_ascii=False) + ";</script><script>" + js + "</script>")

    s = s.replace("</head>", head + "</head>", 1)
    s = re.sub(r"(<body[^>]*>)", lambda mm: mm.group(1) + wrap(BG), s, count=1)
    s = s.replace('<header class="log-head">', '<header class="log-head">' + band, 1)
    s = re.sub(r'(<h1 class="log-title">.*?</h1>)', lambda mm: trow_open + mm.group(1) + trow_close, s, count=1, flags=re.S)
    s = s.replace("</main>", foot + "</main>", 1)
    s = s.replace("</body>", script + "</body>", 1)
    return s

def main(argv):
    args, scenes_path = [], None
    it = iter(argv)
    for a in it:
        if a == "--scenes": scenes_path = next(it)
        else: args.append(a)
    if not args:
        print(__doc__); return 1
    inp = args[0]
    out = args[1] if len(args) > 1 else re.sub(r"(\.html?)$", r" (칼데아)\1", inp, flags=re.I)
    scenes = json.load(open(scenes_path, encoding="utf-8")) if scenes_path else {}
    src = open(inp, encoding="utf-8").read()
    if 'class="log-title"' not in src:
        print("! 정리된 로그 형식(log-title)이 아님:", inp); return 2
    open(out, "w", encoding="utf-8").write(themed(src, scenes))
    print("저장:", out)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
