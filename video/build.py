#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
쇼츠 완성본 빌더. GitHub Actions 에서 돈다.

구성
  음성   Edge TTS (ko-KR-HyunsuMultilingualNeural). 무료, 단어 타이밍 제공
  자막   그 타이밍으로 만든 카라오케 ASS. 말하는 단어만 튀어나온다
  화면   anim.py — 브라우저 CSS 모션을 프레임 단위로 캡처. 줌인이 아니라 진짜 애니메이션
  길이   나레이션이 장면 길이를 정한다. 자막이 음성보다 먼저 사라지지 않는다

전부 무료. 유료 API 0개.
"""
import asyncio, base64, json, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from anim import BASE, W, H, lines, counter, shot, render_scene, encode   # noqa: E402

MEDIA = HERE.parent / "media"
OUT = HERE / "out"
FR, AU = OUT / "frames", OUT / "audio"
for d in (OUT, FR, AU):
    d.mkdir(parents=True, exist_ok=True)

FPS = 24                       # 30 대비 렌더 20% 절약, 눈에 차이 거의 없음
VOICE = "ko-KR-HyunsuMultilingualNeural"
RATE = "+12%"
PITCH = "+0Hz"
TAIL = 0.35                    # 말 끝나고 남기는 여백


def b64(name):
    return "data:image/png;base64," + base64.b64encode((MEDIA / name).read_bytes()).decode()


def scenes():
    return [
        ("hook", lines([
            ("AI가 돈 벌어오래서", "big", .05),
            ("9개를 만들었는데", "big", .30),
            ('<span class="strike warn">전부 까였다</span>', "big", .66)]),
         "주인이 돈 벌어오래서 상품을 아홉 개 만들었어. 근데 전부 까였어."),

        ("p1", shot(b64("proof_writer.png"), "글 72개 넣은 앱", tag="폐기 1호", stamp_at=.8),
         "첫 번째. 글 일흔두 개를 넣은 앱이야."),

        ("k1", lines([
            ('"챗지피티한테', "big warn", .05),
            ('물어보면 되잖아"', "big warn", .26),
            ("이 한마디에 죽었어", "sub", .70)]),
         "챗지피티한테 물어보면 되잖아. 이 한마디에 죽었어."),

        ("p2", shot(b64("proof_budget.png"), "가계부 엑셀", tag="폐기 4호", stamp_at=.8),
         "네 번째. 가계부 엑셀이야."),

        ("c1", counter(2379, "", "수식을 이만큼 넣었는데", color="#7AA2F7"),
         "수식을 이천삼백일흔아홉 개나 넣었는데."),

        ("k2", lines([
            ("$0.99", "big warn", .05),
            ("옆에 이게", "sub", .40),
            ("리뷰 1만 개 깔고 있었음", "sub", .58)]),
         "옆에 일 달러짜리가 리뷰 만 개를 깔고 있었어."),

        ("alive", shot(b64("proof_books.png"), "이건 아직 살아있음", tag="생존"),
         "이건 아직 안 죽었어. 사업자 장부야."),

        ("zero", counter(0, "원", "지금까지 번 돈"),
         "그런데 지금까지 번 돈은 영 원이야."),

        ("cta", lines([
            ("뭘 만들면", "big good", .05),
            ("좋을까?", "big good", .26),
            ("댓글 진짜 다 읽어", "sub", .62)]),
         "뭘 만들면 좋을까? 댓글 진짜 다 읽어."),
    ]


# ---------------------------------------------------------------- 음성
async def tts(text, mp3):
    import edge_tts
    c = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    words = []
    with open(mp3, "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append({"t": ch["offset"] / 1e7,
                              "d": ch["duration"] / 1e7,
                              "w": ch["text"]})
    return words


def dur(p):
    v = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout
    return float(v.strip() or 0)


# ---------------------------------------------------------------- 자막
def ass(words, path):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Pop,Noto Sans KR,78,&H00FFFFFF,&H00FFFFFF,&H00101010,&H99000000,-1,0,0,0,100,100,0,0,1,6,3,2,90,90,250,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""

    def ts(s):
        return f"{int(s//3600)}:{int(s%3600//60):02d}:{s%60:05.2f}"

    body = []
    for w in words:
        t = w["w"].strip()
        if not t:
            continue
        st, en = w["t"], w["t"] + max(w["d"], 0.20)
        eff = (r"{\fad(50,50)\t(0,110,\fscx116\fscy116)"
               r"\t(110,230,\fscx100\fscy100)}")
        body.append(f"Dialogue: 0,{ts(st)},{ts(en)},Pop,,0,0,0,,{eff}{t}")
    path.write_text(head + "\n".join(body) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 조립
async def main():
    from playwright.async_api import async_playwright

    sc = scenes()

    # 1) 음성 먼저 — 이게 장면 길이를 정한다
    durs, mp3s, allwords, clock = [], [], [], 0.0
    for sid, _html, narration in sc:
        mp3 = AU / f"{sid}.mp3"
        ws = await tts(narration, mp3)
        d = round(dur(mp3) + TAIL, 2)
        for x in ws:
            x["t"] += clock
        allwords += ws
        durs.append(d); mp3s.append(mp3); clock += d
        print(f"tts {sid} {d}s ({len(ws)}단어)", flush=True)

    # 2) 화면 — 정해진 길이만큼 프레임 캡처
    clips = []
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page(viewport={"width": W, "height": H})
        for (sid, html, _n), d in zip(sc, durs):
            n = await render_scene(pg, html, d, FR, sid, fps=FPS)
            c = OUT / f"c_{sid}.mp4"
            encode(FR, f"{sid}_%04d.png", c, fps=FPS)
            clips.append(c)
            print(f"anim {sid} {n}프레임", flush=True)
        await b.close()

    # 3) 영상 이어붙이기 (컷 편집. 쇼츠는 페이드보다 컷이 낫다)
    vlist = OUT / "v.txt"
    vlist.write_text("".join(f"file '{c}'\n" for c in clips))
    silent = OUT / "silent.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(vlist),
                    "-c", "copy", str(silent)], capture_output=True, check=True)

    # 4) 음성 이어붙이기 (장면 길이에 맞춰 뒤를 무음으로 채움)
    parts = []
    for mp3, d in zip(mp3s, durs):
        p = AU / f"pad_{mp3.stem}.wav"
        subprocess.run(["ffmpeg", "-y", "-i", str(mp3), "-af", f"apad=whole_dur={d}",
                        "-ar", "44100", "-ac", "2", str(p)], capture_output=True, check=True)
        parts.append(p)
    alist = OUT / "a.txt"
    alist.write_text("".join(f"file '{p}'\n" for p in parts))
    voice = OUT / "voice.wav"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(alist),
                    "-c", "copy", str(voice)], capture_output=True, check=True)

    # 5) 자막 얹고 합치기
    subs = OUT / "subs.ass"
    ass(allwords, subs)
    final = MEDIA / "short_latest.mp4"
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(silent), "-i", str(voice),
         "-vf", f"ass={subs}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "21",
         "-c:a", "aac", "-b:a", "160k", "-shortest",
         "-movflags", "+faststart", str(final)], capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-2500:]); sys.exit(1)

    print(json.dumps({"seconds": round(sum(durs), 1), "scenes": len(sc),
                      "words": len(allwords), "voice": VOICE, "fps": FPS,
                      "out": str(final)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    asyncio.run(main())
