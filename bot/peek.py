#!/usr/bin/env python3
"""
남의 계정을 읽을 수 있는 경로가 있는지 실제로 호출해서 결론을 낸다.

추측하지 않는다. 문서가 서로 엇갈리므로 전부 불러보고 되는 것만 남긴다.
약관을 우회하는 방법(스크래핑, 비공개 엔드포인트)은 시도하지 않는다.
공식 API로 되는지 아닌지만 본다.

TARGET : 볼 사람의 핸들 (기본 juvin950)
결과는 peek_result.json 에 남는다.
"""
import json, os, pathlib, sys

import requests

sys.path.insert(0, str(pathlib.Path(__file__).parent))

TARGET = os.environ.get("TARGET", "juvin950").strip().lstrip("@")
IG_TOKEN = os.environ.get("INSTA_TOKEN", "").strip()
TH_TOKEN = os.environ.get("THREADS_TOKEN", "").strip()

out = {"target": TARGET, "checks": {}}


def record(name, ok, **kw):
    out["checks"][name] = {"ok": ok, **kw}
    tag = "OK  " if ok else "FAIL"
    print(f"[{tag}] {name}: {json.dumps(kw, ensure_ascii=False)[:300]}")


def call(name, url, params):
    try:
        r = requests.get(url, params=params, timeout=30)
        body = r.json()
    except Exception as e:                                    # noqa: BLE001
        record(name, False, error=f"{type(e).__name__}: {e}")
        return None
    if r.status_code >= 400 or "error" in body:
        err = body.get("error", {})
        record(name, False, status=r.status_code, code=err.get("code"),
               error=err.get("message", json.dumps(body)[:200]))
        return None
    record(name, True, result=body)
    return body


DISCOVERY = (
    "business_discovery.username(%s)"
    "{username,name,biography,website,followers_count,follows_count,media_count,"
    "media.limit(12){caption,like_count,comments_count,permalink,timestamp,media_type}}"
) % TARGET

if IG_TOKEN:
    # 내 인스타 id 먼저
    me = call("ig_whoami", "https://graph.instagram.com/v23.0/me",
              {"fields": "user_id,username,account_type", "access_token": IG_TOKEN})
    uid = (me or {}).get("user_id") or (me or {}).get("id")

    if uid:
        # 1) Instagram Login 토큰으로 business_discovery
        call("ig_business_discovery",
             f"https://graph.instagram.com/v23.0/{uid}",
             {"fields": DISCOVERY, "access_token": IG_TOKEN})

        # 2) 같은 토큰을 facebook 그래프에 (스펙상 다른 로그인 방식이라 아마 실패)
        call("fb_business_discovery",
             f"https://graph.facebook.com/v23.0/{uid}",
             {"fields": DISCOVERY, "access_token": IG_TOKEN})
else:
    record("ig_whoami", False, error="INSTA_TOKEN 없음")

if TH_TOKEN:
    # 3) 스레드 키워드 검색으로 이 사람 이름이 잡히는지 (앱 심사 필요할 것으로 예상)
    call("threads_keyword_search",
         "https://graph.threads.net/v1.0/keyword_search",
         {"q": TARGET, "search_type": "TOP",
          "fields": "id,text,username,permalink,timestamp",
          "limit": 10, "access_token": TH_TOKEN})

    # 4) 공개 프로필 직접 조회가 되는지
    call("threads_profile_lookup",
         f"https://graph.threads.net/v1.0/{TARGET}",
         {"fields": "id,username", "access_token": TH_TOKEN})
else:
    record("threads_keyword_search", False, error="THREADS_TOKEN 없음")

pathlib.Path(__file__).parent.parent.joinpath("peek_result.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + "\n")

ok = [k for k, v in out["checks"].items() if v.get("ok")]
print(f"\n요약: 성공 {len(ok)}/{len(out['checks'])} -> {ok}")
