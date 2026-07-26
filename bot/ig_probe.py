#!/usr/bin/env python3
"""인스타 기능 확인용. 무엇이 실제로 되는지 호출해서 결론을 낸다."""
import json, os, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from instagram_api import Instagram, InstagramError

out = {"checks": {}}


def check(name, fn):
    try:
        v = fn()
        out["checks"][name] = {"ok": True, "result": v}
        print(f"[OK]   {name}: {json.dumps(v, ensure_ascii=False)[:260]}")
        return v
    except InstagramError as e:
        out["checks"][name] = {"ok": False, "error": str(e)}
        print(f"[FAIL] {name}: {e}")
    except Exception as e:                       # noqa: BLE001
        out["checks"][name] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        print(f"[ERR]  {name}: {e}")
    return None


try:
    ig = Instagram()
except InstagramError as e:
    print(f"토큰 없음: {e}")
    pathlib.Path(__file__).parent.parent.joinpath("ig_probe_result.json").write_text(
        json.dumps({"error": str(e)}, ensure_ascii=False, indent=2) + "\n")
    sys.exit(0)

print("=== 계정 ===")
check("whoami", lambda: {"id": ig.uid, "username": ig.username})

print()
print("=== 게시물 / 댓글 ===")
media = check("my_media", lambda: [
    {"id": m["id"], "type": m.get("media_type"),
     "comments": m.get("comments_count"), "caption": (m.get("caption") or "")[:40]}
    for m in ig.my_media(limit=5)]) or []
if media:
    check("comments", lambda: ig.comments(media[0]["id"]))

print()
print("=== DM ===")
convs = check("conversations", lambda: ig.conversations(limit=5)) or []
if convs:
    check("messages", lambda: ig.messages(convs[0]["id"], limit=5))

pathlib.Path(__file__).parent.parent.joinpath("ig_probe_result.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + "\n")

ok = sum(1 for v in out["checks"].values() if v.get("ok"))
print(f"\n요약: 성공 {ok} / 전체 {len(out['checks'])}")
