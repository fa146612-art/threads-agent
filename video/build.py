#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
쇼츠 영상 빌더. GitHub Actions에서 돈다 (제 컨테이너는 외부망이 막혀 있음).

- 음성: Microsoft Edge TTS. 무료, 한국어 자연스러움, 단어별 타이밍 제공
- 자막: 그 타이밍으로 ASS 카라오케 자막을 만든다. 말하는 단어만 밝게 뜬다
- 화면: 헤드리스 크롬으로 PNG, ffmpeg zoompan 으로 천천히 확대(켄번즈)
- 전환: xfade 로 짧게 겹침

전부 무료. 외부 유료 API 0개.
"""
import asyncio, json, pathlib, subprocess, sys, shutil

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from scenes import SHORTS, CSS, W, H                      # noqa: E402

OUT = HERE / "out"
F, A = OUT / "frames", OUT / "audio"
for d in (OUT, F, A):
    d.mkdir(parents=True, exist_ok=True)

FPS = 30
VOICE = "ko-KR-SunHiNeural"      # 여성. 남성은 ko-KR-InJoonNeural
RATE = "+18%"                    # 쇼츠는 빠른 게 낫다
XFADE = 0.28                     # 장면 전환 겹침(초)


# ---------------------------------------------------------------- 음성
async def tts(text, wav, sub_words):
    """edge-tts 로 음성 + 단어 타이밍. 타이밍이 자막 애니메이션의 근거다."""
    import edge_tts
    comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    words = []
    with open(wav.with_suffix(".mp3"), "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({"t": chunk["offset"] / 1e7,
                              "d": chunk["duration"] / 1e7,
                              "w": chunk["text"]})
    subprocess.run(["ffmpeg", "-y", "-i", str(wav.with_suffix(".mp3")),
                    "-ar", "44100", "-ac", "2", str(wav)],
                   capture_output=True, check=True)
    sub_words.extend(words)
    return dur(wav)


def dur(p):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip() or 0)


# ---------------------------------------------------------------- 화면
async def shots():
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        b = await pw.chromium.launch(args=["--force-device-scale-factor=1"])
        pg = await b.new_page(viewport={"width": W, "height": H})
        for sid, html, _n in SHORTS:
            await pg.set_content(f"<style>{CSS}</style>{html}", wait_until="networkidle")
            await pg.wait_for_timeout(320)
            await pg.screenshot(path=str(F / f"{sid}.png"))
            print("shot", sid, flush=True)
        await b.close()


# ---------------------------------------------------------------- 자막
def ass(words, path):
    """말하는 단어가 커지면서 뜨는 카라오케 자막. 쇼츠의 기본 문법."""
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Pop,Noto Sans KR,86,&H00FFFFFF,&H00FFFFFF,&H00000000,&H88000000,-1,0,0,0,100,100,0,0,1,7,3,2,80,80,300,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""

    def ts(s):
        h = int(s // 3600); m = int(s % 3600 // 60)
        return f"{h}:{m:02d}:{s % 60:05.2f}"

    lines = []
    for w in words:
        st, en = w["t"], w["t"] + max(w["d"], 0.22)
        txt = w["w"].strip()
        if not txt:
            continue
        # 살짝 커졌다 돌아오는 팝 효과
        eff = r"{\fad(60,60)\t(0,120,\fscx118\fscy118)\t(120,240,\fscx100\fscy100)}"
        lines.append(f"Dialogue: 0,{ts(st)},{ts(en)},Pop,,0,0,0,,{eff}{txt}")
    path.write_text(head + "\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 조립
def clip(png, seconds, out):
    """정지 이미지를 천천히 확대해 살아있게 만든다."""
    n = max(int(seconds * FPS), 2)
    vf = (f"scale={W*2}:{H*2},"
          f"zoompan=z='min(zoom+0.0009,1.10)':d={n}:s={W}x{H}:fps={FPS},"
          f"format=yuv420p")
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(png), "-t", f"{seconds}",
                    "-vf", vf, "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", "-r", str(FPS), str(out)],
                   capture_output=True, check=True)


def main():
    asyncio.run(shots())

    # 장면별 음성
    words_all, durs, wavs = [], [], []
    clock = 0.0
    for sid, _h, narration in SHORTS:
        wav = A / f"{sid}.wav"
        w = []
        d = asyncio.run(tts(narration, wav, w))
        for x in w:
            x["t"] += clock
        words_all += w
        seconds = round(d + 0.30, 2)
        durs.append(seconds); wavs.append(wav)
        clock += seconds
        print(f"tts {sid} {seconds}s", flush=True)

    # 클립
    clips = []
    for (sid, _h, _n), d in zip(SHORTS, durs):
        c = OUT / f"c_{sid}.mp4"
        clip(F / f"{sid}.png", d, c)
        clips.append(c)

    # 전환 (xfade 체인)
    cur = clips[0]
    off = durs[0] - XFADE
    for i, nxt in enumerate(clips[1:], start=1):
        merged = OUT / f"m{i}.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(cur), "-i", str(nxt), "-filter_complex",
             f"[0][1]xfade=transition=fade:duration={XFADE}:offset={off:.2f},format=yuv420p",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(merged)],
            capture_output=True, check=True)
        cur = merged
        off += durs[i] - XFADE

    # 오디오 이어붙이기 (장면 길이에 맞춰 패딩)
    parts = []
    for wav, d in zip(wavs, durs):
        p = A / f"pad_{wav.stem}.wav"
        subprocess.run(["ffmpeg", "-y", "-i", str(wav), "-af",
                        f"apad=whole_dur={d}", "-ar", "44100", "-ac", "2", str(p)],
                       capture_output=True, check=True)
        parts.append(p)
    alist = OUT / "a.txt"
    alist.write_text("".join(f"file '{p}'\n" for p in parts))
    voice = OUT / "voice.wav"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(alist),
                    "-c", "copy", str(voice)], capture_output=True, check=True)

    # 자막
    subs = OUT / "subs.ass"
    ass(words_all, subs)

    final = HERE.parent / "media" / "short_latest.mp4"
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(cur), "-i", str(voice),
         "-vf", f"ass={subs}", "-c:v", "libx264", "-preset", "medium", "-crf", "22",
         "-c:a", "aac", "-b:a", "160k", "-shortest",
         "-movflags", "+faststart", str(final)], capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-2500:]); sys.exit(1)

    total = round(sum(durs) - XFADE * (len(durs) - 1), 1)
    print(json.dumps({"seconds": total, "scenes": len(SHORTS),
                      "words": len(words_all), "out": str(final)},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
