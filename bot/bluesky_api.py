"""Bluesky (AT Protocol) client.

The reason this exists: Threads blocks the one thing that actually grows an
account - replying to other people's posts. Bluesky allows it, plus likes,
follows and search, with no app review and no cost.

Auth is an App Password, generated in Bluesky settings. Nothing else.
    BSKY_HANDLE    e.g. zerowon.bsky.social
    BSKY_PASSWORD  the app password (xxxx-xxxx-xxxx-xxxx)
"""
import json, os, time, datetime, re
import requests

BASE = "https://bsky.social/xrpc"
PUBLIC = "https://public.api.bsky.app/xrpc"


class BlueskyError(RuntimeError):
    pass


class Bluesky:
    def __init__(self, handle=None, password=None):
        self.handle = (handle or os.environ.get("BSKY_HANDLE", "")).strip()
        self.password = (password or os.environ.get("BSKY_PASSWORD", "")).strip()
        if not self.handle or not self.password:
            raise BlueskyError("BSKY_HANDLE / BSKY_PASSWORD 가 비어 있음")
        self.did = None
        self.jwt = None
        self._login()

    # ---------------------------------------------------------- transport
    def _req(self, method, url, auth=True, **kw):
        headers = kw.pop("headers", {})
        if auth and self.jwt:
            headers["Authorization"] = f"Bearer {self.jwt}"
        for attempt in range(3):
            try:
                r = requests.request(method, url, headers=headers, timeout=30, **kw)
            except requests.RequestException as e:
                if attempt == 2:
                    raise BlueskyError(f"network: {e}")
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code == 429 and attempt < 2:
                time.sleep(10 * (attempt + 1))
                continue
            try:
                body = r.json()
            except ValueError:
                raise BlueskyError(f"non-JSON {r.status_code}: {r.text[:250]}")
            if r.status_code >= 400:
                raise BlueskyError(f"{r.status_code} {body.get('error')}: "
                                   f"{body.get('message', '')[:250]}")
            return body
        raise BlueskyError("exhausted retries")

    def _login(self):
        d = self._req("POST", f"{BASE}/com.atproto.server.createSession", auth=False,
                      json={"identifier": self.handle, "password": self.password})
        self.did, self.jwt = d["did"], d["accessJwt"]

    def _create(self, collection, record):
        return self._req("POST", f"{BASE}/com.atproto.repo.createRecord",
                         json={"repo": self.did, "collection": collection,
                               "record": record})

    # ---------------------------------------------------------- helpers
    @staticmethod
    def _now():
        return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _facets(text):
        """Turn #tags and links into real facets so they are clickable."""
        facets, b = [], text.encode()
        for m in re.finditer(r"#(\w+)", text):
            facets.append({
                "index": {"byteStart": len(text[:m.start()].encode()),
                          "byteEnd": len(text[:m.end()].encode())},
                "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": m.group(1)}]})
        for m in re.finditer(r"https?://\S+", text):
            facets.append({
                "index": {"byteStart": len(text[:m.start()].encode()),
                          "byteEnd": len(text[:m.end()].encode())},
                "features": [{"$type": "app.bsky.richtext.facet#link", "uri": m.group(0)}]})
        return facets

    def _upload(self, path):
        with open(path, "rb") as f:
            data = f.read()
        d = self._req("POST", f"{BASE}/com.atproto.repo.uploadBlob",
                      headers={"Content-Type": "image/png"}, data=data)
        return d["blob"]

    # ---------------------------------------------------------- writes
    def post(self, text, image_path=None, alt="", reply_to=None):
        """Publish. reply_to is a post dict from search/timeline - we reply to it.

        Replying to strangers is the whole point of using this platform.
        """
        rec = {"$type": "app.bsky.feed.post", "text": text[:300],
               "createdAt": self._now(), "langs": ["ko"]}
        facets = self._facets(text[:300])
        if facets:
            rec["facets"] = facets
        if image_path:
            rec["embed"] = {"$type": "app.bsky.embed.images",
                            "images": [{"alt": alt or text[:100],
                                        "image": self._upload(image_path)}]}
        if reply_to:
            parent = {"uri": reply_to["uri"], "cid": reply_to["cid"]}
            root = (reply_to.get("record", {}).get("reply", {}) or {}).get("root") or parent
            rec["reply"] = {"root": root, "parent": parent}
        return self._create("app.bsky.feed.post", rec)

    def like(self, post):
        return self._create("app.bsky.feed.like", {
            "$type": "app.bsky.feed.like", "createdAt": self._now(),
            "subject": {"uri": post["uri"], "cid": post["cid"]}})

    def follow(self, did):
        return self._create("app.bsky.graph.follow", {
            "$type": "app.bsky.graph.follow", "createdAt": self._now(), "subject": did})

    # ---------------------------------------------------------- reads
    def search(self, q, limit=25, lang="ko"):
        """Find other people's posts. No approval needed, unlike Threads."""
        p = {"q": q, "limit": limit}
        if lang:
            p["lang"] = lang
        return self._req("GET", f"{BASE}/app.bsky.feed.searchPosts", params=p).get("posts", [])

    def notifications(self, limit=50):
        return self._req("GET", f"{BASE}/app.bsky.notification.listNotifications",
                         params={"limit": limit}).get("notifications", [])

    def my_posts(self, limit=20):
        return self._req("GET", f"{BASE}/app.bsky.feed.getAuthorFeed",
                         params={"actor": self.did, "limit": limit}).get("feed", [])

    def profile(self):
        return self._req("GET", f"{BASE}/app.bsky.actor.getProfile",
                         params={"actor": self.did})

# secrets 등록 확인용 트리거 2131
