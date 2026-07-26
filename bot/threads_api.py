"""Minimal, dependable client for Meta's official Threads API."""
import json, os, time
import requests

BASE = "https://graph.threads.net/v1.0"
PUBLISH_DELAY = float(os.environ.get("THREADS_PUBLISH_DELAY", "5"))

POST_FIELDS = "id,media_type,text,permalink,timestamp,username"
REPLY_FIELDS = "id,text,username,timestamp,permalink,replied_to,is_reply,root_post,has_replies"
INSIGHT_FIELDS = "views,likes,replies,reposts,quotes"


class ThreadsError(RuntimeError):
    pass


class Threads:
    def __init__(self, token=None):
        self.token = (token or os.environ.get("THREADS_TOKEN", "")).strip()
        if not self.token:
            raise ThreadsError("THREADS_TOKEN is empty. Set it as a repository secret.")
        self._uid = None
        self._username = None

    # ---------------------------------------------------------- transport
    def _call(self, method, path, **params):
        params["access_token"] = self.token
        url = f"{BASE}/{path.lstrip('/')}"
        for attempt in range(3):
            try:
                r = requests.request(
                    method, url,
                    params=params if method == "GET" else None,
                    data=None if method == "GET" else params,
                    timeout=30,
                )
            except requests.RequestException as e:
                if attempt == 2:
                    raise ThreadsError(f"network: {e}")
                time.sleep(2 * (attempt + 1))
                continue
            try:
                body = r.json()
            except ValueError:
                raise ThreadsError(f"non-JSON {r.status_code}: {r.text[:300]}")
            if r.status_code >= 400 or "error" in body:
                err = body.get("error", {})
                msg = err.get("message", json.dumps(body)[:300])
                # transient throttling -> back off and retry
                if err.get("code") in (4, 17, 32, 613) and attempt < 2:
                    time.sleep(5 * (attempt + 1))
                    continue
                raise ThreadsError(f"{r.status_code} code={err.get('code')}: {msg}")
            return body
        raise ThreadsError("exhausted retries")

    def get(self, path, **p):
        return self._call("GET", path, **p)

    def post(self, path, **p):
        return self._call("POST", path, **p)

    # ---------------------------------------------------------- identity
    @property
    def uid(self):
        if self._uid is None:
            d = self.get("me", fields="id,username")
            self._uid, self._username = d["id"], d.get("username")
        return self._uid

    @property
    def username(self):
        if self._username is None:
            _ = self.uid
        return self._username

    # ---------------------------------------------------------- reads
    def my_posts(self, limit=25):
        return self.get(f"{self.uid}/threads", fields=POST_FIELDS, limit=limit).get("data", [])

    def replies(self, media_id):
        return self.get(f"{media_id}/replies", fields=REPLY_FIELDS,
                        reverse="false").get("data", [])

    def insights(self, media_id):
        try:
            data = self.get(f"{media_id}/insights", metric=INSIGHT_FIELDS).get("data", [])
            return {d["name"]: d.get("values", [{}])[0].get("value", 0) for d in data}
        except ThreadsError:
            return {}

    def limits(self):
        try:
            d = self.get(f"{self.uid}/threads_publishing_limit",
                         fields="quota_usage,config,reply_quota_usage,reply_config")
            return d.get("data", [{}])[0]
        except ThreadsError:
            return {}

    SEARCH_FIELDS = "id,text,username,timestamp,permalink,media_type"

    def search(self, q, limit=25, recent=True, media_type=None):
        """Find other people's public posts by keyword.

        This is the growth engine: commenting on posts from accounts 2-10x
        your size is the single highest-leverage action available, and Threads
        surfaces your replies in your own followers' feeds too.
        """
        params = {"q": q, "search_type": "RECENT" if recent else "TOP",
                  "fields": self.SEARCH_FIELDS, "limit": limit}
        if media_type:
            params["media_type"] = media_type
        return self.get("keyword_search", **params).get("data", [])

    # ---------------------------------------------------------- writes
    def publish(self, text, reply_to_id=None, image_url=None):
        """Create a container then publish it. Returns the new media id.

        An image roughly triples engagement, so image_url is worth using
        whenever there is anything worth showing. The URL must be publicly
        reachable - raw.githubusercontent.com works and costs nothing.
        """
        if image_url:
            params = {"media_type": "IMAGE", "image_url": image_url, "text": text}
        else:
            params = {"media_type": "TEXT", "text": text}
        if reply_to_id:
            params["reply_to_id"] = reply_to_id
        container = self.post(f"{self.uid}/threads", **params)
        time.sleep(PUBLISH_DELAY)
        last = None
        for attempt in range(5):
            try:
                res = self.post(f"{self.uid}/threads_publish", creation_id=container["id"])
                return res.get("id")
            except ThreadsError as e:
                last = e
                time.sleep(PUBLISH_DELAY * (attempt + 1))
        raise ThreadsError(f"publish failed: {last}")

    def publish_thread(self, parts, reply_to_id=None):
        ids, prev = [], reply_to_id
        for part in parts:
            mid = self.publish(part, reply_to_id=prev)
            ids.append(mid)
            prev = mid
            time.sleep(PUBLISH_DELAY)
        return ids
