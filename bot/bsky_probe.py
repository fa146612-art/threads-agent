#!/usr/bin/env python3
"""블루스카이 기능 확인. 무엇이 실제로 되는지 호출해서 결론을 낸다."""
import json, os, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from bluesky_api import Bluesky, BlueskyError

import datetime
OUT = pathlib.Path(__file__).parent.parent / "bsky_probe_result.json"
_h = os.environ.get("BSKY_HANDLE", "")
_p = os.environ.get("BSKY_PASSWORD", "")
out = {
    "ran_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "secrets": {"handle_len": len(_h), "password_len": len(_p),
                "handle_tail": _h[-12:] if _h else ""},
    "checks": {},
}


def check(name, fn):
    try:
        v = fn()
        out["checks"][name] = {"ok": True, "result": v}
        print(f"[OK]   {name}: {json.dumps(v, ensure_ascii=False)[:240]}")
        return v
    except Exception as e:                       # noqa: BLE001
        out["checks"][name] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        print(f"[FAIL] {name}: {e}")
        return None


try:
    b = Bluesky()
except BlueskyError as e:
    print(f"로그인 실패: {e}")
    out["error"] = str(e)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    sys.exit(0)

print("=== 계정 ===")
check("profile", lambda: {k: b.profile().get(k)
                          for k in ("handle", "displayName", "followersCount",
                                    "followsCount", "postsCount")})

print()
print("=== 남의 글 검색 (스레드에서 막혔던 기능) ===")
found = []
for q in ["AI", "부업", "글쓰기"]:
    rows = check(f"search:{q}", lambda q=q: [
        {"handle": p["author"]["handle"], "uri": p["uri"], "cid": p["cid"],
         "text": (p["record"].get("text") or "")[:70],
         "likes": p.get("likeCount", 0)}
        for p in b.search(q, limit=5)])
    if rows:
        found += [r for r in rows if r["handle"] != b.handle]

print()
print("=== 알림 ===")
check("notifications", lambda: len(b.notifications(limit=20)))

print()
print("=== 쓰기 (DRY_RUN=0 일 때만 실제 실행) ===")
if os.environ.get("DRY_RUN", "1") == "1":
    out["checks"]["write"] = {"ok": None, "note": "DRY_RUN",
                              "reply_candidate": found[0] if found else None}
    print(f"[DRY]  답글 후보: {found[0]['handle'] if found else '없음'}")
else:
    check("post", lambda: b.post("테스트. 곧 지울게."))

OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
ok = sum(1 for v in out["checks"].values() if v.get("ok"))
print(f"\n요약: 성공 {ok} / 전체 {len(out['checks'])}")
