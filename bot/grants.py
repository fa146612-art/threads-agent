#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
정부 지원사업 공고 수집기. GitHub Actions 에서 돈다 (컨테이너는 외부망 차단).

소스
  기업마당  bizinfo.go.kr  — 공식 오픈API (인증키 BIZINFO_KEY)
  K-Startup data.go.kr     — 공식 오픈API (인증키 DATA_GO_KR_KEY)

두 키가 없으면 프로브 모드로만 돌면서 응답 형태를 grants_probe.json 에 남긴다.
키가 들어오면 fetch 모드가 신규 공고를 grants.json 에 누적한다.

원칙: 여기서 모으는 건 '재료'다. 발행 글은 매번 새로 쓴다. 공고문 복붙은 하지 않는다.
"""
import datetime
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).parent.parent
PROBE = ROOT / "grants_probe.json"
STORE = ROOT / "grants.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

BIZINFO_URL = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
KSTARTUP_URL = ("https://apis.data.go.kr/B552735/kisedKstartupService01/"
                "getAnnouncementInformation01")


def get(url, params, timeout=40):
    req = urllib.request.Request(
        url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- 프로브
def probe():
    """응답이 실제로 어떻게 생겼는지 먼저 본다. 문서만 믿고 파서부터 짜지 않는다."""
    out = {"checked_at": now(), "sources": []}

    p = {"dataType": "json", "searchCnt": "3"}
    key = os.environ.get("BIZINFO_KEY", "").strip()
    if key:
        p["crtfcKey"] = key
    try:
        st, body = get(BIZINFO_URL, p)
        out["sources"].append({"name": "bizinfo", "keyed": bool(key),
                               "status": st, "sample": body[:6000]})
    except Exception as e:                                 # noqa: BLE001
        out["sources"].append({"name": "bizinfo", "keyed": bool(key),
                               "error": repr(e)})

    key = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if key:
        try:
            st, body = get(KSTARTUP_URL, {"serviceKey": key, "page": "1",
                                          "perPage": "3", "returnType": "json"})
            out["sources"].append({"name": "kstartup", "keyed": True,
                                   "status": st, "sample": body[:6000]})
        except Exception as e:                             # noqa: BLE001
            out["sources"].append({"name": "kstartup", "keyed": True,
                                   "error": repr(e)})
    else:
        out["sources"].append({"name": "kstartup", "keyed": False,
                               "note": "DATA_GO_KR_KEY 없음 - 건너뜀"})

    PROBE.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False)[:1200])


# ---------------------------------------------------------------- 수집
def norm_bizinfo(item):
    """기업마당 응답 한 건을 공통 형태로. 필드명이 다르면 원본을 raw 에 남겨 뒀다가 고친다."""
    g = item.get
    return {
        "source": "bizinfo",
        "id": g("pblancId") or g("pblancUrl") or g("pblancNm"),
        "title": g("pblancNm"),
        "org": g("jrsdInsttNm") or g("excInsttNm"),
        "field": g("pldirSportRealmLclasCodeNm"),
        "target": g("trgetNm"),
        "period": g("reqstBeginEndDe"),
        "url": ("https://www.bizinfo.go.kr" + g("pblancUrl")
                if g("pblancUrl", "").startswith("/") else g("pblancUrl")),
        "hashtags": g("hashtags"),
        "raw_keys": sorted(item.keys()),
    }


def fetch():
    key = os.environ.get("BIZINFO_KEY", "").strip()
    if not key:
        print("BIZINFO_KEY 없음 - probe 모드로 전환")
        return probe()

    st, body = get(BIZINFO_URL, {"crtfcKey": key, "dataType": "json",
                                 "searchCnt": "60"})
    data = json.loads(body)
    items = (data.get("jsonArray") if isinstance(data, dict) else data) or []
    if not isinstance(items, list):
        raise SystemExit(f"예상 밖 응답 구조: {str(data)[:500]}")

    store = {"updated_at": None, "items": []}
    if STORE.exists():
        store = json.loads(STORE.read_text(encoding="utf-8"))
    known = {it.get("id") for it in store["items"]}

    fresh = []
    for it in items:
        n = norm_bizinfo(it)
        if n["id"] and n["id"] not in known:
            fresh.append(n)

    store["items"] = (fresh + store["items"])[:800]        # 오래된 것부터 밀어냄
    store["updated_at"] = now()
    store["last_fetch_count"] = len(items)
    store["last_new_count"] = len(fresh)
    STORE.write_text(json.dumps(store, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"수집 {len(items)}건, 신규 {len(fresh)}건, 보관 {len(store['items'])}건")


if __name__ == "__main__":
    if "--fetch" in sys.argv:
        fetch()
    else:
        probe()
