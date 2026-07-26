# -*- coding: utf-8 -*-
"""
진짜 애니메이션 엔진.

ffmpeg 로 이미지를 줌인하는 건 애니메이션이 아니다.
여기서는 브라우저에서 CSS/Web Animations 로 실제 모션을 만들고,
프레임마다 시간을 정확히 되감아 캡처한다. 모션그래픽 툴이 하는 방식과 같다.

시간을 코드로 제어하므로 렌더가 느려도 결과 타이밍은 정확하다.
"""
import asyncio, pathlib, subprocess

W, H, FPS = 1080, 1920, 30

FONTS = ("@import url('https://fonts.googleapis.com/css2?"
         "family=Noto+Sans+KR:wght@400;500;700;900&display=swap');")

BASE = FONTS + """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;overflow:hidden;background:#0B0D11}
body{font-family:'Noto Sans KR',sans-serif;-webkit-font-smoothing:antialiased}
.stage{width:1080px;height:1920px;position:relative;overflow:hidden}

/* 배경이 아주 천천히 흐른다. 정지 화면 느낌을 없앤다 */
.bg{position:absolute;inset:-20%;
  background:radial-gradient(circle at 28% 22%, rgba(122,162,247,.22), transparent 52%),
             radial-gradient(circle at 76% 78%, rgba(196,142,224,.18), transparent 52%);
  animation:drift 18s ease-in-out infinite alternate}
@keyframes drift{from{transform:translate(-3%,-2%) scale(1.05)}
                 to{transform:translate(3%,2%) scale(1.15)}}

.center{position:absolute;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;padding:0 78px;text-align:center}

/* 한 줄씩 아래에서 솟아오르며 흐림이 걷힌다 */
.line{opacity:0;transform:translateY(70px) scale(.94);filter:blur(14px);
  animation:rise .62s cubic-bezier(.16,1,.3,1) forwards}
@keyframes rise{to{opacity:1;transform:none;filter:blur(0)}}

.big{font-size:118px;font-weight:900;color:#fff;line-height:1.24;
  letter-spacing:-.045em;text-shadow:0 10px 50px rgba(0,0,0,.55)}
.sub{font-size:48px;font-weight:700;color:#98A1AE;margin-top:40px;line-height:1.45}
.accent{color:#7AA2F7}.warn{color:#F0736F}.good{color:#57C99A}

/* 취소선이 왼쪽에서 오른쪽으로 그어진다 */
.strike{position:relative;display:inline-block}
.strike::after{content:'';position:absolute;left:-6px;right:-6px;top:52%;height:9px;
  background:#F0736F;border-radius:6px;transform-origin:left center;transform:scaleX(0);
  animation:draw .42s cubic-bezier(.65,0,.35,1) forwards}
@keyframes draw{to{transform:scaleX(1)}}

/* 도장이 위에서 내려꽂히고 살짝 튄다 */
.stamp{position:absolute;top:50%;left:50%;
  border:12px solid #F0736F;border-radius:26px;padding:22px 66px;
  background:rgba(11,13,17,.62);
  font-size:112px;font-weight:900;color:#F0736F;letter-spacing:.08em;
  transform:translate(-50%,-50%) rotate(-10deg) scale(3.4);opacity:0;
  animation:slam .5s cubic-bezier(.2,1.6,.4,1) forwards}
@keyframes slam{60%{opacity:1;transform:translate(-50%,-50%) rotate(-10deg) scale(.92)}
                80%{transform:translate(-50%,-50%) rotate(-10deg) scale(1.06)}
                100%{opacity:1;transform:translate(-50%,-50%) rotate(-10deg) scale(1)}}

/* 화면 캡처가 밀려 들어온다 */
.shotwrap{width:100%;border-radius:26px;overflow:hidden;border:1px solid #262C36;
  background:#fff;box-shadow:0 34px 90px rgba(0,0,0,.65);position:relative;
  opacity:0;transform:translateY(90px) scale(.96);
  animation:rise .7s cubic-bezier(.16,1,.3,1) forwards}
.shotwrap img{width:100%;display:block}
.shade{position:absolute;inset:0;background:rgba(11,13,17,.34)}

.handle{position:absolute;bottom:150px;left:0;right:0;text-align:center;
  font-size:34px;color:#3C4452;font-weight:700;letter-spacing:.1em}
.tag{position:absolute;top:120px;left:0;right:0;text-align:center;
  font-size:36px;color:#7AA2F7;font-weight:900;letter-spacing:.28em;
  opacity:0;animation:rise .5s ease forwards}
"""


def counter(target, unit="", label="", color="#F0736F", digits=None):
    """0에서 목표 숫자까지 올라가는 카운터. 숫자가 그냥 떠 있는 것보다 훨씬 세다."""
    return f"""
<div class="stage"><div class="bg"></div><div class="center">
  <div class="line" style="animation-delay:.05s">
    <span id="num" style="font-size:360px;font-weight:900;color:#fff;
      line-height:.85;letter-spacing:-.07em">0</span><span
      style="font-size:130px;font-weight:900;color:{color}">{unit}</span>
  </div>
  <div class="line sub" style="animation-delay:.5s;color:{color};font-size:56px;
    font-weight:900;white-space:pre-line">{label}</div>
</div><div class="handle">@zero.won_ai</div></div>
<script>
window.__anim = (t) => {{
  const p = Math.min(Math.max((t-0.15)/1.35,0),1);
  const e = 1-Math.pow(1-p,3);
  const v = Math.round({target}*e);
  document.getElementById('num').textContent =
    {'v.toLocaleString()' if (digits is None) else 'v.toFixed(%d)' % digits};
}};
</script>"""


def lines(items, tag=""):
    """여러 줄이 시간차로 솟아오른다. items = [(텍스트, 클래스, 지연초)]"""
    body = "".join(
        f'<div class="line {cls}" style="animation-delay:{d}s">{t}</div>'
        for t, cls, d in items)
    tg = f'<div class="tag" style="animation-delay:.05s">{tag}</div>' if tag else ""
    return f"""<div class="stage"><div class="bg"></div>{tg}
      <div class="center">{body}</div>
      <div class="handle">@zero.won_ai</div></div>"""


def shot(img_b64, cap, tag="", stamp_at=None):
    st = (f'<div class="stamp" style="animation-delay:{stamp_at}s">폐기</div>'
          if stamp_at is not None else "")
    tg = f'<div class="tag" style="animation-delay:.05s">{tag}</div>' if tag else ""
    return f"""<div class="stage"><div class="bg"></div>{tg}
      <div class="center">
        <div class="shotwrap" style="animation-delay:.08s">
          <img src="{img_b64}"><div class="shade"></div>{st}
        </div>
        <div class="line big" style="animation-delay:.55s;font-size:60px;margin-top:52px">{cap}</div>
      </div><div class="handle">@zero.won_ai</div></div>"""


# ---------------------------------------------------------------- 렌더
async def render_scene(pg, html, seconds, outdir, prefix, fps=FPS, motion=None):
    """시간을 코드로 되감으며 프레임을 뜬다. 타이밍은 렌더 속도와 무관하게 정확하다.

    움직임은 보통 1.5~2초면 끝난다. 그 뒤는 정지 화면이라 다시 그릴 이유가 없어서,
    움직이는 구간만 캡처하고 나머지는 마지막 프레임을 복사한다.
    프레임 수가 3분의 1로 줄고 결과는 같다.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    await pg.set_content(f"<style>{BASE}</style>{html}", wait_until="networkidle")
    await pg.wait_for_timeout(260)                    # 폰트 로드

    total = int(seconds * fps)
    if motion is None:                                 # 애니메이션이 끝나는 시점
        motion = await pg.evaluate("""() => {
            let end = 0;
            document.getAnimations().forEach(a => {
              const t = a.effect && a.effect.getComputedTiming();
              if (t) end = Math.max(end, ((t.delay||0) + (t.activeDuration||0)) / 1000);
            });
            return Math.min(Math.max(end, 0.8), 3.0);
        }""")
    live = min(int((motion + 0.35) * fps), total)

    for i in range(live):
        t = i / fps
        await pg.evaluate("""(t) => {
            document.getAnimations().forEach(a => {
              try { a.pause(); a.currentTime = t * 1000; } catch(e) {}
            });
            if (window.__anim) window.__anim(t);
        }""", t)
        await pg.screenshot(path=str(outdir / f"{prefix}_{i:04d}.png"))

    if live < total:                                   # 남은 구간은 마지막 프레임 복사
        last = outdir / f"{prefix}_{live-1:04d}.png"
        data = last.read_bytes()
        for i in range(live, total):
            (outdir / f"{prefix}_{i:04d}.png").write_bytes(data)
    return total


def encode(frames_dir, pattern, out, fps=FPS):
    subprocess.run(["ffmpeg", "-y", "-framerate", str(fps),
                    "-i", str(frames_dir / pattern),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", str(out)], capture_output=True, check=True)
    return out
