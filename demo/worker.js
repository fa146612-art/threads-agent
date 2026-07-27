/**
 * zero.won_ai — Threads API demo screen for Meta App Review.
 *
 * Purpose: Meta's reviewers must be able to watch, and reproduce themselves,
 * the full path: logged out -> log in -> see the consent screen listing
 * `threads_keyword_search` -> grant it -> use it -> see the result.
 *
 * Our production agent is a GitHub Actions script with no screen, so there is
 * nothing to record. This is the smallest real screen that shows the permission
 * being granted and then used. One file, no database, no build step.
 *
 * The interface is written in English first (Korean underneath) on purpose:
 * "screencast is not in English and has no subtitles" is a common rejection.
 *
 * Deploy (free tier, no credit card):
 *   npx wrangler deploy
 *   npx wrangler secret put THREADS_APP_SECRET
 * Vars in wrangler.toml: THREADS_APP_ID, REDIRECT_URI
 */

const AUTH = "https://threads.net/oauth/authorize";
const GRAPH = "https://graph.threads.net";
const API = `${GRAPH}/v1.0`;

const SCOPES = [
  "threads_basic",
  "threads_content_publish",
  "threads_manage_replies",
  "threads_manage_insights",
  "threads_keyword_search",
].join(",");

/* ------------------------------------------------------------------ shell */

const page = (body, { title = "Threads Keyword Search Demo" } = {}) => `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${title}</title>
<style>
 :root{--bg:#0E1014;--fg:#F2F4F8;--sub:#8A93A3;--accent:#5B8CFF;--line:#232833}
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.65 -apple-system,
      BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;-webkit-font-smoothing:antialiased}
 .wrap{max-width:720px;margin:0 auto;padding:48px 20px 80px}
 .kicker{color:var(--accent);font-weight:700;font-size:12px;letter-spacing:.09em;
         text-transform:uppercase}
 h1{font-size:27px;line-height:1.3;margin:8px 0 4px;font-weight:800}
 .ko{color:var(--sub);font-size:14px;margin:0 0 4px}
 .card{border:1px solid var(--line);border-radius:12px;padding:20px;margin:18px 0;
       background:rgba(255,255,255,.02)}
 .btn{display:inline-block;background:var(--accent);color:#fff;text-decoration:none;
      padding:13px 22px;border-radius:9px;font-weight:700;border:0;font-size:16px;
      cursor:pointer;font-family:inherit}
 .btn.ghost{background:transparent;border:1px solid var(--line);color:var(--sub);
            padding:8px 14px;font-size:14px;font-weight:600}
 input[type=text],textarea{width:100%;background:#171B22;border:1px solid var(--line);
      color:var(--fg);border-radius:9px;padding:13px 14px;font:inherit;font-size:16px}
 textarea{min-height:96px;resize:vertical}
 label{display:block;font-size:13px;color:var(--sub);font-weight:700;margin:0 0 7px;
       letter-spacing:.04em;text-transform:uppercase}
 .meta{color:var(--sub);font-size:13px;margin:0 0 8px}
 .txt{white-space:pre-wrap;margin:0 0 12px}
 .row{display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap}
 .row>div{flex:1;min-width:220px}
 a{color:var(--accent)}
 .ok{border-left:3px solid #3FB950}
 .bad{border-left:3px solid #F85149}
 .step{color:var(--sub);font-size:13px;border-top:1px solid var(--line);
       margin-top:36px;padding-top:16px}
 code{background:#171B22;padding:2px 6px;border-radius:5px;font-size:13.5px}
</style></head><body><div class="wrap">${body}</div></body></html>`;

const esc = (s = "") =>
  String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const html = (b, status = 200) =>
  new Response(page(b), { status, headers: { "content-type": "text/html;charset=utf-8" } });

const cookie = (req, name) =>
  (req.headers.get("cookie") || "")
    .split(";").map((v) => v.trim().split("="))
    .find(([k]) => k === name)?.[1];

/* -------------------------------------------------------------- api calls */

async function graph(url, init) {
  const r = await fetch(url, init);
  const body = await r.json().catch(() => ({}));
  if (!r.ok || body.error) {
    throw new Error(body.error?.message || `HTTP ${r.status}`);
  }
  return body;
}

/* ------------------------------------------------------------------ views */

const loggedOut = (note = "") => `
  <div class="kicker">Step 1 of 3</div>
  <h1>Threads Keyword Search Demo</h1>
  <p class="ko">스레드 키워드 검색 데모 · @zero.won_ai</p>

  <div class="card">
    <p><strong>You are not logged in.</strong> Click below to authorize this app with
       your Threads account. The consent screen will list
       <code>threads_keyword_search</code> among the permissions requested.</p>
    <p class="ko">로그인되어 있지 않습니다. 아래를 누르면 동의 화면이 뜹니다.</p>
    <p><a class="btn" href="/login">Log in with Threads</a></p>
  </div>

  ${note}

  <div class="card">
    <p class="meta">WHAT THIS APP DOES</p>
    <p>It operates one publicly self-identified AI account. It searches public posts for
       a few Korean-language keywords, reads what it finds, and writes a single reply
       written specifically for that post. It posts no links and sends no bulk messages.</p>
    <p class="meta" style="margin-top:14px">
      <a href="https://fa146612-art.github.io/threads-agent/">Privacy policy &amp; data deletion</a>
      &nbsp;·&nbsp;
      <a href="https://github.com/fa146612-art/threads-agent">Source code</a>
    </p>
  </div>`;

const searchView = (me, q = "", results = null, note = "") => `
  <div class="kicker">Step ${results ? "3" : "2"} of 3</div>
  <h1>${results ? "Keyword search results" : "Search public posts"}</h1>
  <p class="ko">${results ? "검색 결과 — 답글을 하나 골라 씁니다" : "키워드로 공개 게시물 검색"}</p>
  <p class="meta">Signed in as <strong>@${esc(me)}</strong> ·
     permission <code>threads_keyword_search</code> granted ·
     <a href="/logout">log out</a></p>

  ${note}

  <form class="card" method="POST" action="/search">
    <label for="q">Keyword / 키워드</label>
    <div class="row">
      <div><input id="q" type="text" name="q" value="${esc(q)}"
                  placeholder="e.g. 챗지피티 포기" required></div>
      <button class="btn" type="submit">Search</button>
    </div>
  </form>

  ${results === null ? "" : results.length === 0
    ? `<div class="card">No public posts matched this keyword.<br>
         <span class="ko">이 키워드로 나온 공개 게시물이 없습니다.</span></div>`
    : results.map((p) => `
      <div class="card">
        <p class="meta">@${esc(p.username)} · ${esc((p.timestamp || "").slice(0, 10))}
           ${p.permalink ? `· <a href="${esc(p.permalink)}" target="_blank">view on Threads</a>` : ""}</p>
        <p class="txt">${esc(p.text || "(no text)")}</p>
        <form method="POST" action="/reply">
          <input type="hidden" name="reply_to_id" value="${esc(p.id)}">
          <input type="hidden" name="q" value="${esc(q)}">
          <label for="t-${esc(p.id)}">Your reply to this post / 이 글에 쓸 답글</label>
          <textarea id="t-${esc(p.id)}" name="text" required
            placeholder="Write a reply about this specific post."></textarea>
          <p style="margin:10px 0 0"><button class="btn" type="submit">Publish reply</button></p>
        </form>
      </div>`).join("")}

  <p class="step">This is the whole app. Log in → search public posts with
     <code>threads_keyword_search</code> → reply to one of them. Nothing else is stored
     except the reply ID, so the same post is never answered twice.</p>`;

/* ---------------------------------------------------------------- routing */

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const path = url.pathname;
    const token = cookie(req, "th");
    const setTok = (t) =>
      `th=${t}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=5184000`;

    /* --- start OAuth: this is the click the screencast must show ------- */
    if (path === "/login") {
      const to = new URL(AUTH);
      to.searchParams.set("client_id", env.THREADS_APP_ID);
      to.searchParams.set("redirect_uri", env.REDIRECT_URI);
      to.searchParams.set("scope", SCOPES);
      to.searchParams.set("response_type", "code");
      return Response.redirect(to.toString(), 302);
    }

    if (path === "/logout") {
      return new Response(null, {
        status: 302,
        headers: { location: "/", "set-cookie": "th=; Path=/; Max-Age=0" },
      });
    }

    /* --- OAuth callback: short-lived code -> long-lived token ---------- */
    if (path === "/callback") {
      const code = url.searchParams.get("code");
      if (!code) {
        return html(loggedOut(`<div class="card bad"><strong>Authorization was cancelled.</strong>
          <br><span class="ko">동의가 취소됐습니다.</span></div>`));
      }
      try {
        const form = new FormData();
        form.set("client_id", env.THREADS_APP_ID);
        form.set("client_secret", env.THREADS_APP_SECRET);
        form.set("grant_type", "authorization_code");
        form.set("redirect_uri", env.REDIRECT_URI);
        form.set("code", code);
        const short = await graph(`${GRAPH}/oauth/access_token`,
          { method: "POST", body: form });

        const long = await graph(
          `${GRAPH}/access_token?grant_type=th_exchange_token` +
          `&client_secret=${encodeURIComponent(env.THREADS_APP_SECRET)}` +
          `&access_token=${encodeURIComponent(short.access_token)}`);

        return new Response(null, {
          status: 302,
          headers: { location: "/", "set-cookie": setTok(long.access_token) },
        });
      } catch (e) {
        return html(loggedOut(
          `<div class="card bad"><strong>Login failed.</strong><br>${esc(e.message)}</div>`), 400);
      }
    }

    if (!token) return html(loggedOut());

    let me;
    try {
      me = await graph(`${API}/me?fields=id,username&access_token=${encodeURIComponent(token)}`);
    } catch {
      return new Response(null, {
        status: 302,
        headers: { location: "/", "set-cookie": "th=; Path=/; Max-Age=0" },
      });
    }

    /* --- the permission in use ----------------------------------------- */
    if (path === "/search" && req.method === "POST") {
      const q = ((await req.formData()).get("q") || "").toString().trim();
      try {
        const r = await graph(
          `${API}/keyword_search?q=${encodeURIComponent(q)}&search_type=TOP` +
          `&fields=id,text,username,permalink,timestamp` +
          `&access_token=${encodeURIComponent(token)}`);
        return html(searchView(me.username, q, (r.data || []).slice(0, 10)));
      } catch (e) {
        return html(searchView(me.username, q, null,
          `<div class="card bad"><strong>Search failed.</strong><br>${esc(e.message)}
           <br><span class="ko">토큰에 threads_keyword_search 권한이 없으면 여기서 막힙니다.</span></div>`));
      }
    }

    /* --- reply: create container, then publish it ---------------------- */
    if (path === "/reply" && req.method === "POST") {
      const f = await req.formData();
      const q = (f.get("q") || "").toString();
      try {
        const mk = new FormData();
        mk.set("media_type", "TEXT");
        mk.set("text", (f.get("text") || "").toString());
        mk.set("reply_to_id", (f.get("reply_to_id") || "").toString());
        mk.set("access_token", token);
        const c = await graph(`${API}/${me.id}/threads`, { method: "POST", body: mk });

        const pub = new FormData();
        pub.set("creation_id", c.id);
        pub.set("access_token", token);
        const done = await graph(`${API}/${me.id}/threads_publish`,
          { method: "POST", body: pub });

        return html(searchView(me.username, q, null,
          `<div class="card ok"><strong>Reply published.</strong>
            Reply ID <code>${esc(done.id)}</code> — stored so this post is never
            answered twice.<br>
            <span class="ko">답글이 게시됐습니다. 같은 글에 두 번 달지 않도록 ID만 저장합니다.</span>
          </div>`));
      } catch (e) {
        return html(searchView(me.username, q, null,
          `<div class="card bad"><strong>Reply failed.</strong><br>${esc(e.message)}</div>`));
      }
    }

    return html(searchView(me.username));
  },
};
