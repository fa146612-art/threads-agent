#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한국어 TTS 목소리 비교. Actions 에서 돈다.

같은 문장을 여러 목소리·속도로 뽑아 하나의 mp3 로 이어붙인다.
사이에 어떤 설정인지 말해주니 듣기만 하면 고를 수 있다.
"""
import asyncio, pathlib, subprocess, json

HERE = pathlib.Path(__file__).parent
OUT = HERE / "voices"
OUT.mkdir(parents=True, exist_ok=True)

LINE = ("주인이 돈 벌어오래서 상품을 아홉 개 만들었는데 전부 까였어. "
        "지금까지 번 돈은 영 원이야.")

# (라벨, 목소리, 속도, 피치)
CANDIDATES = [
    ("A 선희 기본",        "ko-KR-SunHiNeural",              "+0%",  "+0Hz"),
    ("B 선희 빠르게",      "ko-KR-SunHiNeural",              "+15%", "+0Hz"),
    ("C 인준 남성",        "ko-KR-InJoonNeural",             "+0%",  "+0Hz"),
    ("D 인준 빠르게",      "ko-KR-InJoonNeural",             "+15%", "+0Hz"),
    ("E 현수 멀티링구얼",  "ko-KR-HyunsuMultilingualNeural", "+0%",  "+0Hz"),
    ("F 현수 빠르게",      "ko-KR-HyunsuMultilingualNeural", "+15%", "+0Hz"),
    ("G 현수 낮게",        "ko-KR-HyunsuMultilingualNeural", "+8%",  "-8Hz"),
]


async def speak(text, voice, rate, pitch, path):
    import edge_tts
    c = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await c.save(str(path))


async def main():
    import edge_tts
    vs = await edge_tts.list_voices()
    ko = sorted({v["ShortName"] for v in vs if v["Locale"].startswith("ko")})
    print("사용 가능한 한국어 목소리:", json.dumps(ko, ensure_ascii=False, indent=1))

    parts = []
    for label, voice, rate, pitch in CANDIDATES:
        if voice not in ko:
            print("건너뜀(없음):", voice)
            continue
        tag = OUT / f"{label[0]}_tag.mp3"
        body = OUT / f"{label[0]}_body.mp3"
        await speak(label, "ko-KR-SunHiNeural", "+0%", "+0Hz", tag)
        await speak(text=LINE, voice=voice, rate=rate, pitch=pitch, path=body)
        parts += [tag, body]
        print("생성", label, voice, rate, pitch, flush=True)

    lst = OUT / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    final = HERE.parent / "media" / "voice_compare.mp3"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c:a", "libmp3lame", "-b:a", "160k", str(final)],
                   capture_output=True, check=True)
    print("saved:", final)


if __name__ == "__main__":
    asyncio.run(main())
