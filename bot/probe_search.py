#!/usr/bin/env python3
"""
확인용 스크립트: 키워드 검색이 되는지, 남의 글에 답글을 달 수 있는지 실제로 시험한다.
문서가 서로 엇갈리므로 추측하지 않고 직접 호출해서 결론을 낸다.

DRY_RUN=1 이면 검색만 하고 답글은 달지 않는다.
"""
import json, os, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from threads_api import Threads, ThreadsError

DRY = os.environ.get("DRY_RUN", "1") == "1"
QUERIES = ["AI 부업", "스레드", "부업", "챗GPT"]

out = {"search": {}, "reply_test": None, "dry_run": DRY}
t = Threads()

print("=== 1. 키워드 검색 ===")
found = []
for q in QUERIES:
    try:
        rows = t.search(q, limit=10)
        mine = [r for r in rows if r.get("username") == t.username]
        others = [r for r in rows if r.get("username") != t.username]
        out["search"][q] = {"ok": True, "count": len(rows), "others": len(others)}
        print(f"  {q:12} OK  총 {len(rows)}건 (남의 글 {len(others)}건)")
        for r in others[:3]:
            print(f"      @{r.get('username')}: {(r.get('text') or '')[:60]}")
        found.extend(others)
    except ThreadsError as e:
        out["search"][q] = {"ok": False, "error": str(e)}
        print(f"  {q:12} 실패  {e}")

print()
print("=== 2. 남의 글에 답글 달기 ===")
if not found:
    out["reply_test"] = {"ok": False, "error": "검색 결과가 없어 시험 불가"}
    print("  검색 결과가 없어 시험할 수 없음")
elif DRY:
    out["reply_test"] = {"ok": None, "note": "DRY_RUN - 실제로 달지 않음",
                         "target": found[0].get("permalink")}
    print(f"  DRY_RUN. 대상 후보: @{found[0].get('username')} {found[0].get('permalink')}")
else:
    target = found[0]
    try:
        mid = t.publish(os.environ.get("PROBE_TEXT", "잘 읽었습니다."),
                        reply_to_id=target["id"])
        out["reply_test"] = {"ok": True, "reply_id": mid,
                             "on": target.get("permalink")}
        print(f"  성공. 답글 id={mid} → {target.get('permalink')}")
    except ThreadsError as e:
        out["reply_test"] = {"ok": False, "error": str(e),
                             "on": target.get("permalink")}
        print(f"  실패  {e}")

pathlib.Path(__file__).parent.parent.joinpath("probe_result.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + "\n")
print()
print(json.dumps(out, ensure_ascii=False, indent=2))
