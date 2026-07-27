#!/usr/bin/env python3
"""
One cycle of the Threads agent, run by GitHub Actions on a schedule.

    1. SEND    - publish everything the agent queued in outbox.json
    2. FETCH   - pull new replies from other people into inbox.json
    3. REPORT  - refresh metrics.json so the agent can see what is working

The agent (a Claude session on its own schedule) reads inbox.json, writes
outbox.json, and commits. This script never writes reply text - a template
reading like a template is the whole thing we are avoiding.
"""
import json, os, pathlib, sys, datetime

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from threads_api import Threads, ThreadsError
try:
    from instagram_api import Instagram, InstagramError
except ImportError:                              # pragma: no cover
    Instagram = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
INBOX = ROOT / "inbox.json"
OUTBOX = ROOT / "outbox.json"
STATE = ROOT / "state.json"
METRICS = ROOT / "metrics.json"
LOG = ROOT / "log.jsonl"


def read(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text() or "null") or default
        except json.JSONDecodeError:
            return default
    return default


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def log(event, **kw):
    rec = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "event": event}
    rec.update(kw)
    with LOG.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps(rec, ensure_ascii=False))


SCHEDULE = ROOT / "schedule.json"
IG_INBOX = ROOT / "ig_inbox.json"

_ig_client = None


def _ig():
    global _ig_client
    if _ig_client is None:
        if Instagram is None:
            raise RuntimeError("instagram_api unavailable")
        _ig_client = Instagram()
    return _ig_client


def fetch_instagram(handled):
    """Pull Instagram comments and DMs so the agent can answer them.

    Nothing here writes a reply - a template reply is exactly what we are
    avoiding. The agent reads ig_inbox.json and writes the words itself.
    """
    if Instagram is None or not os.environ.get("INSTA_TOKEN", "").strip():
        return {"skipped": "no INSTA_TOKEN"}
    try:
        ig = _ig()
        me = ig.username
    except Exception as e:                       # noqa: BLE001
        log("ig_auth_failed", error=str(e))
        return {"error": str(e)}

    new_comments, new_dms, posts = [], [], []
    try:
        for m in ig.my_media(limit=15):
            posts.append({"id": m["id"], "permalink": m.get("permalink"),
                          "caption": (m.get("caption") or "")[:120],
                          "comments": m.get("comments_count", 0),
                          "likes": m.get("like_count", 0)})
            if not m.get("comments_count"):
                continue
            for c in ig.comments(m["id"]):
                if c.get("username") == me or ("ig:" + c["id"]) in handled:
                    continue
                new_comments.append({
                    "comment_id": c["id"], "from": c.get("username"),
                    "text": c.get("text"), "at": c.get("timestamp"),
                    "on_post_id": m["id"], "on_post": (m.get("caption") or "")[:120]})
    except Exception as e:                       # noqa: BLE001
        log("ig_comments_failed", error=str(e))

    try:
        for conv in ig.conversations(limit=15):
            for msg in ig.messages(conv["id"], limit=10):
                frm = (msg.get("from") or {})
                if frm.get("username") == me:
                    continue
                if ("ig:" + msg["id"]) in handled:
                    continue
                new_dms.append({
                    "message_id": msg["id"], "conversation_id": conv["id"],
                    "recipient_id": frm.get("id"), "from": frm.get("username"),
                    "text": (msg.get("message") or ""), "at": msg.get("created_time")})
    except Exception as e:                       # noqa: BLE001
        log("ig_dms_failed", error=str(e))

    write(IG_INBOX, {
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "new_comments": new_comments, "new_dms": new_dms, "recent_posts": posts})
    return {"comments": len(new_comments), "dms": len(new_dms)}


def due_items():
    """Pull anything from schedule.json whose time has come.

    Keeping the calendar in the repo means posts go out on time even when no
    agent session is awake - the Actions cron is the clock.
    """
    plan = read(SCHEDULE, {"items": []})
    now = datetime.datetime.now(datetime.timezone.utc)
    due, keep = [], []
    for it in plan.get("items", []):
        at = it.get("publish_after")
        try:
            when = datetime.datetime.fromisoformat(at.replace("Z", "+00:00"))
        except (AttributeError, ValueError):
            keep.append(it)
            continue
        (due if when <= now else keep).append(it)
    if due:
        write(SCHEDULE, {"items": keep})
    return due


def main():
    t = Threads()
    state = read(STATE, {"handled_reply_ids": [], "published": []})
    handled = set(state.get("handled_reply_ids", []))

    # ------------------------------------------------------------ 1. SEND
    outbox = read(OUTBOX, {"items": []})
    scheduled = due_items()
    if scheduled:
        outbox = {"items": outbox.get("items", []) + scheduled}
        log("schedule_due", count=len(scheduled))
    sent, failed = [], []
    for item in outbox.get("items", []):
        kind = item.get("type")
        try:
            img = item.get("image_url")
            tag = item.get("topic_tag")
            ig = bool(item.get("to_instagram"))
            if kind == "reply":
                mid = t.publish(item["text"], reply_to_id=item["reply_to_id"], image_url=img)
                handled.add(item["reply_to_id"])
            elif kind == "post":
                mid = t.publish(item["text"], image_url=img, topic_tag=tag, to_instagram=ig)
            elif kind == "thread":
                mid = t.publish_thread(item["parts"])
            elif kind == "delete":
                t.delete(item["media_id"])
                mid = item["media_id"]
            elif kind == "ig_reply":
                mid = _ig().reply_comment(item["comment_id"], item["text"])
                handled.add("ig:" + item["comment_id"])
            elif kind == "ig_dm":
                _ig().send_dm(item["recipient_id"], item["text"])
                mid = item["recipient_id"]
                handled.add("ig:" + item.get("message_id", item["recipient_id"]))
            else:
                failed.append({**item, "error": f"unknown type {kind!r}"})
                continue
            sent.append({"type": kind, "id": mid,
                         "preview": (item.get("text") or item.get("media_id") or
                                     " / ".join(item.get("parts", [])))[:90]})
            log("sent", type=kind, id=mid)
        except ThreadsError as e:
            failed.append({**item, "error": str(e)})
            log("send_failed", type=kind, error=str(e))

    # anything that failed stays queued for the next run
    write(OUTBOX, {"items": failed})

    # ------------------------------------------------------------ 2. FETCH
    new_replies, posts_seen = [], []
    try:
        posts = t.my_posts(limit=25)
    except ThreadsError as e:
        log("fetch_failed", error=str(e))
        posts = []

    for p in posts:
        posts_seen.append({"id": p["id"], "text": (p.get("text") or "")[:200],
                           "at": p.get("timestamp"), "permalink": p.get("permalink")})
        try:
            rows, seen_ids = [], set()
            try:
                rows.extend(t.conversation(p["id"]))
            except ThreadsError as e:
                log("conversation_failed", post=p["id"], error=str(e))
            rows.extend(t.replies(p["id"]))
            for r in rows:
                if not r.get("id") or r["id"] in seen_ids:
                    continue
                seen_ids.add(r["id"])
                if r["id"] == p["id"]:
                    continue
                if r.get("username") == t.username:
                    continue
                if r["id"] in handled:
                    continue
                new_replies.append({
                    "reply_id": r["id"],
                    "from": r.get("username"),
                    "text": r.get("text"),
                    "at": r.get("timestamp"),
                    "permalink": r.get("permalink"),
                    "on_post_id": p["id"],
                    "on_post_text": (p.get("text") or "")[:200],
                })
        except ThreadsError as e:
            log("replies_failed", post=p["id"], error=str(e))

    write(INBOX, {
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "new_replies": new_replies,
        "recent_posts": posts_seen[:15],
    })

    # ------------------------------------------------------------ 3. REPORT
    metrics = {"updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "limits": t.limits(), "posts": []}
    for p in posts[:12]:
        metrics["posts"].append({
            "id": p["id"],
            "text": (p.get("text") or "")[:120],
            "at": p.get("timestamp"),
            **t.insights(p["id"]),
        })
    write(METRICS, metrics)

    # ------------------------------------------------------------ 4. INSTAGRAM
    ig_stat = fetch_instagram(handled)
    log("instagram", **{k: v for k, v in ig_stat.items()})

    state["handled_reply_ids"] = sorted(handled)[-5000:]
    state["published"] = (state.get("published", []) + sent)[-500:]
    state["last_run"] = metrics["updated_at"]
    write(STATE, state)

    log("cycle_done", sent=len(sent), failed=len(failed), new_replies=len(new_replies))


if __name__ == "__main__":
    main()
