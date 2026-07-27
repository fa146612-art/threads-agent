# threads_keyword_search 앱 심사 제출 계획

작성 2026-07-27. 근거는 Meta 공식 문서와 심사 리젝 사유 정리본(맨 아래 출처).

---

## 0. 먼저 알아야 할 것 — 지금 막힌 건 심사 때문이 아닐 수 있다

공식 문서는 이렇게 말한다.

> 앱이 `threads_keyword_search` 승인을 받지 않았으면, **검색은 인증된 사용자 본인의 글에 대해서만 수행된다.**
> 승인 후에는 공개 게시물이 검색된다.

즉 **승인 전에도 호출 자체는 성공해야 한다.** 결과가 내 글로 좁혀질 뿐이다.

그런데 우리가 받은 응답은 이거였다.

```
500 code=10: Application does not have permission for this action
```

호출이 아예 거부됐다. 이건 "승인 안 됨"이 아니라 **토큰에 `threads_keyword_search`
스코프가 처음부터 안 붙어 있다**는 신호로 읽는 게 맞다.

**그래서 순서가 이렇게 된다. 0번을 건너뛰면 심사도 못 넣는다.**
심사에는 화면 녹화가 필수인데, 엔드포인트가 500을 뱉는 상태로는 찍을 화면이 없다.

---

## 1단계 — 토큰에 스코프 다시 붙이기 (오수원님 30분)

### 1-1. 인증 URL

Meta 개발자 콘솔 → 앱 → Threads 사용 사례에서 **Threads 앱 ID**를 확인하고 아래에 넣는다.
(주의: 앱 ID가 두 개 나온다. 페이스북 앱 ID 말고 **Threads 앱 ID**를 쓴다.)

```
https://threads.net/oauth/authorize
  ?client_id=<THREADS_APP_ID>
  &redirect_uri=<등록해둔 리디렉션 URI>
  &scope=threads_basic,threads_content_publish,threads_manage_replies,threads_manage_insights,threads_keyword_search
  &response_type=code
```

핵심은 `scope` 맨 뒤의 **`threads_keyword_search`** 하나다. 지금 토큰에는 이게 없다.

### 1-2. 받은 코드를 장기 토큰으로 바꾼다

단기 토큰(1시간) → 장기 토큰(60일) 교환까지 해야 GitHub Actions에서 쓸 수 있다.
바꾼 토큰을 리포지토리 시크릿 `THREADS_TOKEN` 에 덮어쓴다.

### 1-3. 확인

`peek` 워크플로를 다시 돌린다. `threads_keyword_search` 항목이

- `ok: true` → 성공. 결과가 내 글만 나와도 정상이다. 2단계로 간다.
- 여전히 `code=10` → 스코프 문제가 아니라 앱 설정 문제다. 그때 다시 판단한다.

---

## 2단계 — 심사 넣기 전에 갖춰야 하는 것

리젝은 대부분 내용이 아니라 준비물에서 난다.

- [ ] **개인정보처리방침 URL** — 실제로 열리는 페이지여야 한다. GitHub Pages로 무료.
- [ ] **데이터 삭제 요청 URL** — Meta가 요구한다. 같은 페이지에 섹션으로 둬도 된다.
- [ ] **앱 아이콘 / 카테고리 / 표시 이름** — 비워두면 반려된다.
- [ ] **앱이 Live(게시됨) 상태** — 문서 명시:
      "권한이 앱 심사로 승인되고 **앱이 게시되어야** 역할 없는 사용자가 권한을 부여할 수 있다."
- [ ] **비즈니스 인증** — 고급 액세스에서 요구될 수 있다. 시간이 걸리니 미리 시작한다.
- [ ] **리뷰어가 따라 할 수 있는 화면** ← **이게 제일 큰 문제. 아래 4단계 참고.**

---

## 3단계 — 제출 문구 (영문 원문 + 우리말 뜻)

리뷰어는 영어로 읽는다. 아래를 그대로 붙여 넣으면 된다.
**거짓말을 넣지 않았다.** AI 계정이라는 사실을 먼저 밝히는 쪽이 오히려 안전하다.
숨겼다가 들키면 그때는 영구 반려다.

### How will you use threads_keyword_search?

> Our app operates a single, publicly self-identified AI account (@zero.won_ai)
> that documents an ongoing experiment in public: an AI agent trying to find out
> what kind of help people would actually pay for.
>
> The account states in its bio and in its posts that it is an AI. It does not
> impersonate a human.
>
> We use keyword search to find public posts where people are already discussing
> the specific topics we write about — for example, tasks they attempted with an
> AI assistant and abandoned partway through. Without keyword search, the account
> can only see replies left on its own posts, which means it can never join a
> conversation that is already happening. It can only wait.
>
> When we find a relevant post, we read it and write a single, specific reply
> about that person's post. We do not post links, we do not advertise, and we do
> not send the same text to more than one person. Every reply is written fresh
> for the post it answers.
>
> We search a small number of Korean-language keywords a few times per day, well
> inside the published rate limits.

**우리말 뜻**: 우리는 AI라고 밝힌 계정 하나를 운영한다. 우리가 쓰는 주제를 이미
이야기하고 있는 공개 글을 찾으려고 검색을 쓴다. 검색이 없으면 내 글에 누가 와주기만
기다려야 한다. 찾으면 그 글에 대해서만 답글을 하나 쓴다. 링크도 광고도 복붙도 없다.

### What data will you store?

> We store post IDs and reply IDs so that we never reply to the same post twice.
> The text of a public reply is held only in a working file that is overwritten on
> every run, so only the most recent cycle exists at any time.
>
> We also keep a short learning log of what we got wrong. Quotes in that log come
> from public posts and are stored **without the author's handle** — we do not keep
> a mapping back to the person.
>
> We do not collect email addresses, phone numbers, real names, addresses, payment
> information, or anything from private posts or private profiles. We do not sell or
> share data, and we do not use it for ad targeting.
>
> Anyone can ask us to delete their data by replying to the account or emailing us,
> and we remove it within 7 days. Our privacy policy and deletion request page:
> https://fa146612-art.github.io/threads-agent/

**우리말 뜻**: ID만 남긴다. 답글 원문은 매 실행마다 덮어쓰는 파일에만 있다.
배운 걸 적는 기록에는 인용만 남기고 **핸들은 지운다**. 삭제 요청은 7일 안에 처리한다.

> ⚠️ **2026-07-27 정정.** 이전 초안에는 "본문을 저장하지 않는다"고 적혀 있었는데
> 그건 사실이 아니었다. `notes.md` 에 사람 핸들과 인용을 그대로 적고 있었고
> **이 레포는 공개다.** 그대로 제출했으면 Meta에 거짓을 말하는 게 됐다.
> 그래서 (1) 문구를 실제와 맞게 고쳤고 (2) `notes.md` 의 핸들을 전부 지웠고
> (3) 삭제 요청 페이지를 만들었다. 제출 전에 잡아서 다행이다.

## 4단계 — 화면 녹화 (여기서 대부분 떨어진다)

Meta가 녹화에서 반드시 보길 요구하는 세 가지:

1. **로그아웃 상태에서 시작해 로그인까지 전 과정.** 중간부터 찍으면 반려.
2. **동의 화면에 `threads_keyword_search` 가 보이고, 사용자가 실제로 허용을 누르는 장면.**
3. **그 권한으로 하는 행동과 그 결과.** 검색 → 결과 표시 → 그걸로 무엇을 하는지까지.

자주 나오는 반려 사유:

- 로그인 과정을 안 찍음
- 동의 화면이 안 보이거나 흐릿함
- **리뷰어가 자기 테스트 계정으로 똑같이 재현할 수 없음**
- 요청한 권한 중 하나가 영상에 안 나옴
- 화면이 저해상도거나, 커서가 안 보이거나, **영어가 아닌 화면인데 자막이 없음**
  → 한국어 화면이면 **영어 자막을 반드시 넣는다**
- 적어낸 용도와 영상 속 동작이 다름

### ⚠️ 우리의 진짜 문제

지금 이 봇은 **GitHub Actions에서 도는 스크립트**다. 사람이 보는 화면이 없다.
"로그인해서 동의 누르고 검색 결과를 보는" 장면을 찍을 대상이 존재하지 않는다.
리뷰어가 재현할 수도 없다.

**그래서 심사를 넣으려면 최소한의 웹 화면 하나를 만들어야 한다.** 크게 만들 필요 없다.

- 「Threads로 로그인」 버튼 하나 → Meta 동의 화면으로 보낸다
- 돌아오면 검색창 하나 → 키워드 입력 → 결과 목록 표시
- 결과 옆에 「답글 쓰기」 → 답글이 달리는 것까지 보여준다

이 정도면 세 요구사항을 다 충족한다. GitHub Pages + 작은 서버 하나면 무료로 된다.
제가 만들 수 있다.

---

## 솔직한 위험 평가

- **자동화·봇 용도는 심사에서 보수적으로 본다.** 우리는 AI라는 걸 숨기지 않기로 했으니
  정직하게 쓸 수밖에 없고, 그래서 반려 확률이 낮지 않다.
- 하지만 숨기는 선택지는 없다. 원칙 3번이고, 들키면 계정이 날아간다.
- **한 번에 통과할 거라고 기대하지 않는 게 맞다.** 리젝 사유는 구체적으로 오니
  고쳐서 다시 넣으면 된다. 비용은 시간뿐이고 돈은 안 든다.
- 기간은 보통 며칠~몇 주. 비즈니스 인증이 걸리면 더 길어진다.

## 그래서 지금 할 일 순서

1. **오수원님**: 1단계 — 스코프 다시 붙인 토큰 발급 → 시크릿 교체
2. **저**: `peek` 재실행해서 500이 사라졌는지 확인
3. **저**: 데모 웹 화면 + 개인정보처리방침 페이지 제작
4. **오수원님**: 녹화(제가 대본 드림) → 제출

1번이 안 되면 나머지는 다 의미가 없다. 거기부터 확인한다.

---

## 출처

- Keyword Search — Threads API, Meta for Developers
  https://developers.facebook.com/docs/threads/keyword-search/
- Get Started — Threads API, Meta for Developers
  https://developers.facebook.com/docs/threads/get-started
- Meta App Review Screencast: Why Your Demo Video Gets Rejected (2026)
  https://singhamandeep.com/meta-app-review-screencast-why-your-demo-video-gets-rejected-2026/
