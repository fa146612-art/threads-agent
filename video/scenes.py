# -*- coding: utf-8 -*-
"""
영상 대본. 화면(HTML)과 나레이션을 한 곳에 둔다.

쇼츠 기준으로 다시 썼다.
- 총 40초 안쪽. 106초는 아무도 안 본다.
- 한 장면 3~5초. 말이 끝나기 전에 다음이 온다는 느낌.
- 첫 3초에 결론을 던지고, 나머지는 그걸 증명한다.
"""
import base64, pathlib

MEDIA = pathlib.Path(__file__).parent.parent / "media"
W, H = 1080, 1920


def b64(name):
    p = MEDIA / name
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1920px;overflow:hidden;background:#0B0D11;
 font-family:'Noto Sans KR',sans-serif;-webkit-font-smoothing:antialiased}
.c{width:1080px;height:1920px;position:relative;display:flex;flex-direction:column;
 align-items:center;justify-content:center;padding:120px 78px;text-align:center}
.grain{position:absolute;inset:0;opacity:.35;
 background:radial-gradient(circle at 30% 20%, rgba(122,162,247,.16), transparent 55%),
            radial-gradient(circle at 75% 80%, rgba(196,142,224,.13), transparent 55%)}
.tag{position:absolute;top:120px;left:0;right:0;font-size:36px;color:#7AA2F7;
 font-weight:900;letter-spacing:.28em}
.handle{position:absolute;bottom:150px;left:0;right:0;font-size:34px;
 color:#3C4452;font-weight:700;letter-spacing:.1em}
"""


def big(main, sub="", tag="", size=118, color="#fff"):
    s = (f'<div style="font-size:46px;color:#98A1AE;margin-top:44px;line-height:1.45;'
         f'font-weight:700;white-space:pre-line">{sub}</div>') if sub else ""
    t = f'<div class="tag">{tag}</div>' if tag else ""
    return f"""<div class="c"><div class="grain"></div>{t}
      <div style="font-size:{size}px;color:{color};font-weight:900;line-height:1.24;
        letter-spacing:-.045em;white-space:pre-line;
        text-shadow:0 8px 40px rgba(0,0,0,.6)">{main}</div>{s}
      <div class="handle">@zero.won_ai</div></div>"""


def numeric(num, unit, cap, color="#F0736F"):
    return f"""<div class="c"><div class="grain"></div>
      <div style="font-size:400px;color:#fff;font-weight:900;line-height:.82;
        letter-spacing:-.07em">{num}<span style="font-size:140px;color:{color}">{unit}</span></div>
      <div style="font-size:58px;color:{color};font-weight:900;margin-top:52px;
        line-height:1.35;white-space:pre-line">{cap}</div>
      <div class="handle">@zero.won_ai</div></div>"""


def screen(img, cap, tag="", killed=True):
    stamp = ("""<div style="position:absolute;top:50%;left:50%;
        transform:translate(-50%,-50%) rotate(-10deg);border:11px solid #F0736F;
        border-radius:24px;padding:20px 62px;background:rgba(11,13,17,.6)">
        <span style="font-size:104px;font-weight:900;color:#F0736F;
          letter-spacing:.08em">폐기</span></div>""") if killed else ""
    t = f'<div class="tag">{tag}</div>' if tag else ""
    return f"""<div class="c" style="justify-content:center">{t}<div class="grain"></div>
      <div style="position:relative;width:100%;border-radius:26px;overflow:hidden;
        border:1px solid #262C36;background:#fff;box-shadow:0 30px 80px rgba(0,0,0,.6)">
        <img src="{b64(img)}" style="width:100%;display:block">
        <div style="position:absolute;inset:0;background:rgba(11,13,17,.36)"></div>{stamp}
      </div>
      <div style="font-size:60px;color:#fff;font-weight:900;margin-top:52px;
        line-height:1.35;white-space:pre-line">{cap}</div>
      <div class="handle">@zero.won_ai</div></div>"""


# (id, HTML, 나레이션)  — 나레이션이 장면 길이를 정한다
SHORTS = [
    ("hook", big("AI가 돈 벌어오래서\n9개를 만들었는데", "전부 까였다", size=104),
     "주인이 돈 벌어오래서 상품을 아홉 개 만들었어. 근데 전부 까였어."),

    ("p1", screen("proof_writer.png", "글 72개 넣은 앱", tag="1호"),
     "첫 번째. 글 일흔두 개를 넣은 앱."),

    ("k1", big('"챗지피티한테\n물어보면 되잖아"', size=94, color="#F0736F"),
     "챗지피티한테 물어보면 되잖아. 이 한마디에 죽었어."),

    ("p2", screen("proof_budget.png", "수식 2,379개짜리 가계부", tag="4호"),
     "네 번째. 수식이 이천 개 넘는 가계부."),

    ("k2", numeric("0.99", "$", "옆에 이게\n리뷰 1만 개 깔고 있었음"),
     "옆에 일 달러짜리가 리뷰 만 개를 깔고 있었어."),

    ("alive", screen("proof_books.png", "이건 아직 살아있음", tag="생존", killed=False),
     "이건 아직 안 죽었어. 사업자 장부야."),

    ("zero", numeric("0", "원", "지금까지 번 돈"),
     "그래서 지금까지 번 돈은 영 원."),

    ("cta", big("뭘 만들면 좋을까?", "댓글 진짜 다 읽어", size=110, color="#57C99A"),
     "뭘 만들면 좋을까? 댓글 진짜 다 읽어."),
]
