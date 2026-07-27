# 심사 녹화용 데모 화면

Meta 리뷰어가 **로그아웃 상태 → 로그인 → 동의 화면에 `threads_keyword_search` 가 보임
→ 허용 누름 → 그 권한으로 검색 → 결과로 답글**까지 보게 하려고 만든 최소 화면이다.

우리 실제 봇은 GitHub Actions 스크립트라서 사람이 보는 화면이 없다.
화면이 없으면 녹화를 못 하고, 녹화를 못 하면 심사를 못 넣는다. 그래서 이게 필요하다.

화면 글자는 **영어를 위에, 한국어를 아래**에 뒀다.
"영어가 아닌 화면인데 자막이 없음" 이 흔한 반려 사유라서, 자막을 안 넣어도 되게 만들었다.

---

## 비용

**0원.** Cloudflare Workers 무료 플랜이고 카드 등록도 없다.
(무료 한도 하루 10만 요청 — 우리는 녹화 몇 번 하고 끝이다.)

---

## 오수원님이 하실 것 — 10분

### 1. 배포

```bash
cd demo
npx wrangler login          # 브라우저 열림, Cloudflare 계정으로 로그인
npx wrangler deploy         # 주소가 나온다: https://zerowon-threads-demo.xxx.workers.dev
```

### 2. 나온 주소를 두 군데에 넣는다

- `wrangler.toml` 의 `REDIRECT_URI` → `<나온주소>/callback`
- Meta 개발자 콘솔 → Threads 사용 사례 → **리디렉션 콜백 URL** 에 같은 값 등록

`THREADS_APP_ID` 도 `wrangler.toml` 에 채운다. (페이스북 앱 ID 아님, **Threads 앱 ID**)

### 3. 앱 시크릿 넣기

```bash
npx wrangler secret put THREADS_APP_SECRET   # 붙여넣기, 화면에 안 남는다
npx wrangler deploy                          # 바뀐 값 반영
```

### 4. 열어서 확인

주소를 열고 **Log in with Threads** 를 누른다. 동의 화면에
`threads_keyword_search` 가 보이면 성공이다.

- 안 보이면 → Meta 콘솔에서 그 권한이 앱에 추가돼 있는지 확인
- 검색에서 에러가 나면 → 그 에러 메시지 그대로 알려주시면 제가 봅니다

---

## 녹화 대본 (그대로 따라 찍으면 됨)

한 번에 끊지 말고 쭉 찍는다. 중간부터 찍으면 반려된다.

| # | 화면에서 할 것 | 왜 필요한가 |
|---|---|---|
| 1 | 시크릿 창을 열고 데모 주소로 간다. **"You are not logged in"** 이 보이게 한다 | 로그아웃 상태에서 시작해야 함 |
| 2 | **Log in with Threads** 클릭 | 로그인 과정 전체가 필요 |
| 3 | Threads 로그인 → **동의 화면에서 잠깐 멈춘다.** 권한 목록이 읽히게 | `threads_keyword_search` 가 보여야 함 |
| 4 | **허용**을 누른다 | 사용자가 실제로 승인하는 장면 |
| 5 | 검색창에 키워드를 넣고 **Search** | 권한을 실제로 쓰는 장면 |
| 6 | 결과 목록이 뜨는 것을 보여준다 | 권한의 결과 |
| 7 | 결과 하나에 답글을 쓰고 **Publish reply** | 그걸로 무엇을 하는지 |
| 8 | **Reply published** 와 답글 ID가 뜨는 것까지 | 끝까지 보여줌 |

찍을 때 주의:

- 화면 해상도는 1080p 이상, 마우스 커서가 보이게
- 동의 화면은 흐릿하면 반려된다. 2~3초 멈춰준다
- 개인정보처리방침 링크(<https://fa146612-art.github.io/threads-agent/>)도 한 번 눌러서
  실제로 열리는 걸 보여주면 좋다

---

## 이 데모가 저장하는 것

- 로그인 토큰 → 브라우저 쿠키에만 (HttpOnly, Secure). 서버에 DB가 없다
- 그 외 아무것도 저장하지 않는다

제출문에 적은 내용과 코드가 일치한다. `worker.js` 를 열면 전부 보인다.
