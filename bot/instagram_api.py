"""Instagram client - comments and DMs on our own account.

Unlike Threads keyword search, this needs no App Review as long as we only
touch our own account. Scopes required:
    instagram_business_basic
    instagram_business_manage_comments
    instagram_business_manage_messages
    instagram_business_content_publish   (optional, for posting)
"""
import json, os, time
import requests

BASE = "https://graph.instagram.com/v23.0"


class InstagramError(RuntimeError):
    pass


class Instagram:
    def __init__(self, token=None):
        self.token = (token or os.environ.get("INSTA_TOKEN", "")).strip()
        if not self.token:
            raise InstagramError("INSTA_TOKEN is empty. Set it as a repository secret.")
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
                    timeout=30)
            except requests.RequestException as e:
                if attempt == 2:
                    raise InstagramError(f"network: {e}")
                time.sleep(2 * (attempt + 1))
                continue
            try:
                body = r.json()
            except ValueError:
                raise InstagramError(f"non-JSON {r.status_code}: {r.text[:300]}")
            if r.status_code >= 400 or "error" in body:
                err = body.get("error", {})
                if err.get("code") in (4, 17, 32, 613) and attempt < 2:
                    time.sleep(5 * (attempt + 1))
                    continue
                raise InstagramError(
                    f"{r.status_code} code={err.get('code')}: "
                    f"{err.get('message', json.dumps(body)[:300])}")
            return body
        raise InstagramError("exhausted retries")

    def get(self, path, **p):
        return self._call("GET", path, **p)

    def post(self, path, **p):
        return self._call("POST", path, **p)

    # ---------------------------------------------------------- identity
    @property
    def uid(self):
        if self._uid is None:
            d = self.get("me", fields="user_id,username,account_type")
            self._uid = d.get("user_id") or d.get("id")
            self._username = d.get("username")
        return self._uid

    @property
    def username(self):
        if self._username is None:
            _ = self.uid
        return self._username

    # ---------------------------------------------------------- reads
    MEDIA_FIELDS = "id,caption,media_type,permalink,timestamp,comments_count,like_count"
    COMMENT_FIELDS = "id,text,username,timestamp,replies{id,text,username,timestamp}"

    def my_media(self, limit=25):
        return self.get("me/media", fields=self.MEDIA_FIELDS, limit=limit).get("data", [])

    def comments(self, media_id):
        return self.get(f"{media_id}/comments",
                        fields=self.COMMENT_FIELDS).get("data", [])

    def conversations(self, limit=25):
        """DM threads. Needs instagram_business_manage_messages."""
        return self.get("me/conversations", platform="instagram",
                        fields="id,updated_time,participants",
                        limit=limit).get("data", [])

    def messages(self, conversation_id, limit=20):
        return self.get(f"{conversation_id}/messages",
                        fields="id,created_time,from,to,message",
                        limit=limit).get("data", [])

    # ---------------------------------------------------------- writes
    def reply_comment(self, comment_id, text):
        """Reply under a specific comment on our own post."""
        return self.post(f"{comment_id}/replies", message=text).get("id")

    def comment_on(self, media_id, text):
        return self.post(f"{media_id}/comments", message=text).get("id")

    def send_dm(self, recipient_id, text):
        payload = {"recipient": json.dumps({"id": recipient_id}),
                   "message": json.dumps({"text": text})}
        return self.post("me/messages", **payload)
