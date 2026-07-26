#!/usr/bin/env python3
"""1080x1080 스레드 카드 생성기 (비용 0원, 헤드리스 크롬 캡처).

사용:
    python3 tools/make_card.py out=media/d2_board.png theme=dark \
        kicker="DAY 2" title="오늘 번 돈" big="0원" \
        line="조회수 0 · 팔로워 0 · 댓글 0" foot="@zero.won_ai"

theme: dark(#0E1014) | light(#F4F5F7)
big 은 생략 가능. line 은 여러 번 줄 수 있다(line= 를 반복).
"""
import html
import pathlib
import subprocess
import sys
import tempfile

import shutil

CHROME_CANDIDATES = [
    "/opt/pw-browsers/chromium",
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    shutil.which("chromium"),
    shutil.which("chromium-browser"),
    shutil.which("google-chrome"),
]
CHROME = next(
    (p for p in CHROME_CANDIDATES if p and pathlib.Path(p).is_file()), "chromium"
)

THEMES = {
    "dark": {"bg": "#0E1014", "fg": "#F2F4F8", "sub": "#8A93A3", "accent": "#5B8CFF"},
    "light": {"bg": "#F4F5F7", "fg": "#14171C", "sub": "#6B7280", "accent": "#2563EB"},
}

TPL = """<!doctype html><meta charset="utf-8">
<style>
  @page {{ margin:0 }}
  html,body {{ margin:0; padding:0 }}
  body {{
    width:1080px; height:1080px; background:{bg}; color:{fg};
    font-family:'Noto Sans CJK KR','Noto Sans KR',sans-serif;
    display:flex; flex-direction:column; justify-content:center;
    padding:96px 88px; box-sizing:border-box;
  }}
  .kicker {{ font-size:34px; font-weight:700; letter-spacing:.14em;
             color:{accent}; margin-bottom:28px }}
  .title  {{ font-size:66px; font-weight:900; line-height:1.28;
             letter-spacing:-.02em; margin-bottom:36px }}
  .big    {{ font-size:168px; font-weight:900; line-height:1.05;
             letter-spacing:-.04em; margin:8px 0 40px }}
  .line   {{ font-size:40px; font-weight:500; line-height:1.62; color:{sub};
             margin-bottom:12px }}
  .rule   {{ height:4px; background:{accent}; width:132px; margin:44px 0 0 }}
  .foot   {{ position:absolute; left:88px; bottom:76px; font-size:32px;
             color:{sub}; font-weight:600 }}
</style>
{body}
"""


def main():
    args = {"theme": "dark", "out": "media/card.png"}
    lines = []
    for raw in sys.argv[1:]:
        if "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        if k == "line":
            lines.append(v)
        else:
            args[k] = v

    t = THEMES.get(args["theme"], THEMES["dark"])
    parts = []
    if args.get("kicker"):
        parts.append(f'<div class="kicker">{html.escape(args["kicker"])}</div>')
    if args.get("title"):
        parts.append(f'<div class="title">{html.escape(args["title"])}</div>')
    if args.get("big"):
        parts.append(f'<div class="big">{html.escape(args["big"])}</div>')
    for ln in lines:
        parts.append(f'<div class="line">{html.escape(ln)}</div>')
    parts.append('<div class="rule"></div>')
    if args.get("foot"):
        parts.append(f'<div class="foot">{html.escape(args["foot"])}</div>')

    doc = TPL.format(body="\n".join(parts), **t)
    out = pathlib.Path(args["out"]).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(doc)
        src = f.name

    subprocess.run(
        [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
         "--hide-scrollbars", "--force-device-scale-factor=1",
         "--window-size=1080,1080", f"--screenshot={out}", f"file://{src}"],
        check=True, capture_output=True,
    )
    print(out)


if __name__ == "__main__":
    main()
