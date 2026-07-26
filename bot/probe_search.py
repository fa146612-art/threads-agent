#!/usr/bin/env python3
"""
기능 확인용 프로브. 문서가 서로 엇갈리므로 추측하지 않고 실제로 호출해서 결론을 낸다.
결과는 probe_result.json 에 남는다.

DRY_RUN=1 : 읽기만 한다 (기본)
DRY_RUN=0 : 남의 글에 실제로 답글을 하나 달아본다
DELETE_ID : 값이 있으면 그 게시물 삭제를 시도한다
"""
import json, os, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from threads_api import Threads, ThreadsError

DRY = os.environ.get("DRY_RUN", "1") == "1"
DELETE_ID = os.environ.get("DELETE_ID", "").strip()
QUERIES = ["AI 부업", "스레드", "부업", "챗지피티"]

out = {"dry_run": DRY, "checks": {}}
t = Threads()


def check(name, fn):
    try:
        v = fn()
        out["checks"][name] = {"ok": True, "result": v}
        print(f"[OK]   {name}: {v}")
        return v
    except ThreadsError as e:
        out["checks"][name] = {"ok": False, "error": str(e)}
        print(f"[FAIL] {name}: {e}")
        return None
    except Exception as e:                       # noqa: BLE001
        out["checks"][name] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        print(f"[ERR]  {name}: {e}")
        return None


print("=== 계정 ===")
check("whoami", lambda: {"id": t.uid, "username": t.username})

print()
print("=== 내 글 / 답글 읽기 ===")
posts = check("my_posts", lambda: [
    {"id": p["id"], "text": (p.get("text") or "")[:40]} for p in t.my_posts(limit=5)]) or []
if posts:
    check("read_replies", lambda: len(t.replies(posts[0]["id"])))

print()
print("=== 키워드 검색 ===")
found = []
for q in QUERIES:
    rows = check(f"search:{q}", lambda q=q: [
        {"u": r.get("username"), "id": r["id"], "t": (r.get("text") or "")[:70]}
        for r in t.search(q, limit=8)])
    if rows:
        found.extend([r for r in rows if r["u"] != t.username])

print()
print("=== 남의 글에 답글 ===")
if not found:
    out["checks"]["reply_to_other"] = {"ok": False, "error": "검색 결과 없음"}
    print("[SKIP] 검색 결과가 없어 시험 불가")
elif DRY:
    out["checks"]["reply_to_other"] = {
        "ok": None, "note": "DRY_RUN", "candidate": found[0]}
    print(f"[DRY]  대상 후보 @{found[0]['u']}: {found[0]['t']}")
else:
    tgt = found[0]
    check("reply_to_other",
          lambda: t.publish(os.environ.get("PROBE_TEXT", "잘 봤어요"),
                            reply_to_id=tgt["id"]))

print()
print("=== 삭제 ===")
if DELETE_ID:
    check("delete", lambda: t.delete(DELETE_ID) and "deleted")
else:
    out["checks"]["delete"] = {"ok": None, "note": "DELETE_ID 미지정"}
    print("[SKIP] DELETE_ID 없음")

print()
print("=== 발행 한도 ===")
check("limits", t.limits)

pathlib.Path(__file__).parent.parent.joinpath("probe_result.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + "\n")

ok = sum(1 for v in out["checks"].values() if v.get("ok") is True)
bad = sum(1 for v in out["checks"].values() if v.get("ok") is False)
print(f"\n요약: 성공 {ok} / 실패 {bad}")
