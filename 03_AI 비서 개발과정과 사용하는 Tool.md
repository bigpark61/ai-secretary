
확인된 과제는 **「AI Agent 개발 – 나만의 AI 비서 구축」**입니다. 핵심은 단순 챗봇이 아니라 **시계열 데이터 → 분석·요약 → Firestore 저장 → GPT에 컨텍스트 제공 → 맞춤형 답변 → 웹 서비스 배포**까지 하나의 서비스를 완성하는 것입니다. 최종적으로 데이터 기반 AI 채팅, 데이터 CRUD, 대화기록 저장·불러오기, 배포·문서화가 모두 동작해야 합니다. M1-2.AI Agent 개발 나만의 AI 비서 구축

## 1. 전체 과제 구조부터 이해하기

전체 흐름을 간단히 표현하면 다음과 같습니다.

**시계열 데이터 준비**  
→ **Python으로 분석/요약**  
→ **Firestore 저장**  
→ **FastAPI로 API 제공**  
→ **GPT API에 데이터 요약을 Context로 전달**  
→ **AI 답변 생성**  
→ **대화기록 Firestore 저장**  
→ **HTML/CSS/JavaScript 화면에 표시**  
→ **Render + Vercel 배포**

즉, 이번 과제에서 가장 중요한 개념은 **“내 데이터를 알고 답하는 AI”**입니다.

예를 들어 매출 데이터를 사용한다면 일반 ChatGPT에게

> "이번 달 실적이 어때?"

라고 묻는 것이 아니라, 시스템이 먼저 내 실제 매출 데이터의 평균·최대·최소·최근 추세를 계산하여 GPT에게 알려준 다음 답변하도록 만드는 것입니다. 과제에서는 이를 **데이터 요약을 시스템 프롬프트에 주입하는 컨텍스트 주입 방식**으로 요구하고 있습니다. M1-2.AI Agent 개발 나만의 AI 비서 구축

## 2. 과제 수행은 10단계로 진행하면 됩니다

|단계|수행 내용|주요 Tool/프로그램|결과물|
|---|---|---|---|
|①|개발환경 구축|Python, VS Code, venv|개발환경|
|②|데이터 선정|CSV/Excel 등|100개 이상 데이터|
|③|데이터 분석|Python|평균·최대·최소·추세|
|④|DB 구축|Firebase Firestore|data, conversations|
|⑤|Backend 구축|FastAPI, Pydantic|REST API|
|⑥|AI 연결|OpenAI API|데이터 기반 AI|
|⑦|대화기록 구현|Firestore|대화 저장/조회|
|⑧|Frontend 구축|HTML/CSS/JavaScript|웹 화면|
|⑨|Backend/Frontend 배포|Render, Vercel|실제 서비스 URL|
|⑩|테스트·문서화|Swagger, GitHub README|최종 제출물|

과제 원문에서도 Python 3.10 이상, FastAPI, Uvicorn, Firebase Admin, OpenAI, python-dotenv를 사용하고 Firebase, Render, Vercel 환경을 준비하도록 요구합니다. M1-2.AI Agent 개발 나만의 AI 비서 구축

# 3. 1단계 — 개발환경 구축

먼저 PC에서 개발할 환경을 만듭니다.

추천 프로젝트 구조는 다음과 같습니다.

```
my-ai-secretary/
│
├─ backend/
│   ├─ main.py
│   ├─ routers/
│   │   ├─ data.py
│   │   ├─ chat.py
│   │   └─ conversations.py
│   ├─ services/
│   │   ├─ firebase_service.py
│   │   └─ openai_service.py
│   ├─ models/
│   │   └─ schemas.py
│   ├─ .env
│   └─ requirements.txt
│
├─ frontend/
│   ├─ index.html
│   ├─ style.css
│   └─ app.js
│
└─ README.md
```

여기서 **VS Code**는 개발 작업공간, **Python**은 데이터 분석과 Backend 프로그램 실행, **venv**는 프로젝트 전용 Python 환경을 만드는 역할입니다.

예를 들어 `venv`를 사용하면 다른 Python 프로젝트의 패키지와 충돌하지 않고 이번 과제에 필요한 `fastapi`, `openai`, `firebase-admin` 등을 별도로 관리할 수 있습니다.

# 4. 2단계 — 시계열 데이터 선정

이번 과제에서 상당히 중요한 단계입니다.

과제에서는 **100개 이상의 데이터 포인트**를 준비하고 기간, 데이터 수, 평균·최대·최소 등의 기본 통계와 최근 증가·감소·유지 추세를 만들 수 있어야 합니다. M1-2.AI Agent 개발 나만의 AI 비서 구축

사용자님의 경우에는 예를 들어 **AI 서비스 월별 사용비용**을 주제로 잡아도 좋습니다.

```
date        service       value       memo
2026-01     ChatGPT       30000       Plus
2026-01     Claude        28000       Pro
2026-02     ChatGPT       30000       Plus
2026-02     Claude        28000       Pro
...
```

또는 제조 분야와 연결하여

```
date        equipment     value
2026-01-01  CNC-01        120
2026-01-02  CNC-01        135
...
```

같은 생산량, 불량률, 전력량 등의 데이터도 가능합니다.

**첫 구현에서는 구조가 단순한 월별 비용·매출·생산량 데이터가 가장 편합니다.**

# 5. 3단계 — Python으로 데이터 분석

Python이 데이터를 읽어 다음 정보를 계산합니다.

```
기간
데이터 개수
평균
최대
최소
합계
최근 추세
```

예를 들어 결과가 다음과 같다고 가정합니다.

```
{
  "period": "2026-01 ~ 2026-09",
  "count": 180,
  "average": 5330000,
  "max": 8500000,
  "min": 2100000,
  "trend": "상승"
}
```

이 **Summary가 나중에 GPT가 내 데이터를 이해하게 만드는 핵심 자료**가 됩니다.

따라서 데이터 전체 100~1,000건을 매번 GPT에 보내는 것이 아니라,

**Raw Data → Python 분석 → Summary → GPT**

방식으로 처리하는 것이 이 과제의 중요한 학습 포인트입니다.

# 6. 4단계 — Firebase Firestore 구축

[Firebase](https://firebase.google.com/?utm_source=chatgpt.com)의 **Firestore**는 이번 과제의 데이터베이스 역할을 합니다.

최소 두 개의 Collection을 구성합니다.

```
Firestore
│
├─ data
│   ├─ document1
│   ├─ document2
│   └─ ...
│
└─ conversations
    ├─ conversation1
    ├─ conversation2
    └─ ...
```

`data`에는 분석 대상 데이터를 저장하고, `conversations`에는 AI와 나눈 대화를 저장합니다. 과제에서도 이 두 컬렉션 구조를 명시하고 있습니다. M1-2.AI Agent 개발 나만의 AI 비서 구축

Firestore를 사용하는 이유는 프로그램을 종료해도 데이터를 유지할 수 있기 때문입니다.

즉,

**Frontend → FastAPI → Firestore**

구조로 데이터를 저장합니다.

# 7. 5단계 — FastAPI Backend 구축

[FastAPI](https://fastapi.tiangolo.com/?utm_source=chatgpt.com)는 이번 프로젝트의 **Backend 중심 프로그램**입니다.

Frontend가 직접 Firestore나 GPT를 조작하는 것이 아니라 FastAPI에게 요청합니다.

예를 들어 데이터 관리 API는 다음처럼 구성됩니다.

```
POST   /api/data
GET    /api/data
PUT    /api/data/{id}
DELETE /api/data/{id}

GET    /api/data/summary
```

과제에서 정확히 이 5개 엔드포인트를 요구합니다. M1-2.AI Agent 개발 나만의 AI 비서 구축

여기서 CRUD라는 용어가 중요합니다.

|기능|의미|API|
|---|---|---|
|Create|데이터 생성|POST|
|Read|데이터 조회|GET|
|Update|데이터 수정|PUT|
|Delete|데이터 삭제|DELETE|

그리고 **Pydantic**은 API로 들어오는 데이터를 검사합니다.

예를 들어 사용자가

```
date = 2026-09-25
value = "abc"
```

처럼 숫자가 들어가야 할 `value`에 문자를 입력하면 Pydantic이 오류를 검출하는 식입니다.

# 8. 6단계 — GPT API 연결

이 단계에서 비로소 AI Agent 기능이 들어갑니다.

사용자가 웹에서

> 이번 달 비용이 지난달보다 증가했어?

라고 질문한다고 가정하겠습니다.

처리 과정은 다음과 같습니다.

```
① 사용자 질문

       ↓

② POST /api/chat

       ↓

③ FastAPI

       ↓

④ /api/data/summary 조회

       ↓

⑤ Firestore 데이터 분석 결과

       ↓

⑥ System Prompt 생성

       ↓

⑦ GPT API 호출

       ↓

⑧ AI 답변

       ↓

⑨ 웹 화면 표시
```

과제에서도 `/api/chat`이 먼저 데이터 Summary를 가져와 시스템 프롬프트에 삽입하고 GPT를 호출한 후 대화를 저장하도록 요구합니다. M1-2.AI Agent 개발 나만의 AI 비서 구축

예를 들어 GPT에게 실제로 전달되는 정보는 개념적으로 다음과 같습니다.

```
당신은 데이터 분석 AI 비서입니다.

[사용자 데이터 요약]

기간: 2026-01 ~ 2026-09
데이터수: 180
평균: 5,330,000원
최대: 8,500,000원
최소: 2,100,000원
최근 추세: 상승

위 데이터를 기반으로 질문에 답하세요.

사용자 질문:
이번 달 실적이 어때?
```

이것이 이번 과제에서 말하는 **Context Injection(컨텍스트 주입)**입니다.

# 9. 7단계 — 대화 기록 저장

GPT와 대화한 내용을 Firestore의 `conversations`에 저장합니다.

예를 들어:

```
{
  "title": "9월 실적 분석",
  "created_at": "2026-09-26",
  "messages": [
    {
      "role": "user",
      "content": "이번 달 실적이 어때?"
    },
    {
      "role": "assistant",
      "content": "이번 달 실적은 평균보다 16% 높습니다."
    }
  ]
}
```

필요한 API는 대략 다음과 같습니다.

```
POST   /api/conversations
GET    /api/conversations
GET    /api/conversations/{id}
DELETE /api/conversations/{id}
```

따라서 사용자가 웹에서 **이전 대화**를 선택하면 Firestore에서 과거 메시지를 읽어와 다시 화면에 표시할 수 있습니다. M1-2.AI Agent 개발 나만의 AI 비서 구축

# 10. 8단계 — HTML/CSS/JavaScript Frontend

Frontend는 사용자가 실제로 보는 화면입니다.

이번 과제에서는 React나 Vue가 아니라 **HTML + CSS + JavaScript**를 사용해야 합니다. M1-2.AI Agent 개발 나만의 AI 비서 구축

역할은 명확하게 구분할 수 있습니다.

```
HTML
↓
화면의 구조

CSS
↓
화면 디자인

JavaScript
↓
화면 동작 + FastAPI 호출
```

예를 들어 사용자가 **전송** 버튼을 누르면 JavaScript의 `fetch()`가 작동합니다.

```
사용자
 ↓
index.html
 ↓
app.js
 ↓
fetch()
 ↓
FastAPI
 ↓
GPT
 ↓
FastAPI
 ↓
app.js
 ↓
HTML 화면
```

최종 화면에는 최소한 **AI 채팅 / 데이터 관리 / 데이터 Summary / 이전 대화** 영역이 필요합니다.

# 11. 9단계 — 배포

개발 PC에서만 작동하면 과제가 끝난 것이 아닙니다.

Backend는 [Render](https://render.com/?utm_source=chatgpt.com), Frontend는 [Vercel](https://vercel.com/?utm_source=chatgpt.com)에 배포하도록 과제에서 지정하고 있습니다. M1-2.AI Agent 개발 나만의 AI 비서 구축

전체 구조는 다음과 됩니다.

```
사용자 PC / 스마트폰
        │
        ▼
      Vercel
 HTML / CSS / JavaScript
        │
        │ REST API
        ▼
      Render
      FastAPI
      /     \
     ▼       ▼
Firestore   GPT API
```

그리고 소스코드는 [GitHub](https://github.com/?utm_source=chatgpt.com)에서 관리합니다.

즉 GitHub는 **소스 버전 관리**, Vercel은 **Frontend 서비스**, Render는 **Backend 서비스**라고 이해하면 됩니다.

# 12. 이번 과제에서 사용하는 프로그램과 역할 총정리

|Tool / 프로그램|구분|핵심 역할|
|---|---|---|
|VS Code|개발도구|프로그램 작성|
|Python|언어|데이터 분석 및 Backend|
|venv|Python 환경|프로젝트별 패키지 분리|
|FastAPI|Backend|REST API 서버|
|Uvicorn|서버|FastAPI 실행|
|Pydantic|검증|API 입력 데이터 검증|
|Firebase Admin|DB 연결|Python ↔ Firestore|
|Firestore|Database|데이터·대화 저장|
|OpenAI API|AI|질문 분석 및 답변 생성|
|python-dotenv|보안/환경설정|`.env` 읽기|
|HTML|Frontend|화면 구조|
|CSS|Frontend|화면 디자인|
|JavaScript|Frontend|사용자 동작 및 API 호출|
|fetch()|통신|Frontend → FastAPI 요청|
|Swagger|API 테스트|`/docs`에서 API 시험|
|Git|형상관리|변경사항 관리|
|GitHub|Repository|소스코드 저장·공유|
|Render|Cloud|FastAPI Backend 배포|
|Vercel|Cloud|Frontend 배포|

## 13. 프로그램 간 관계를 이해하는 것이 가장 중요합니다

각 프로그램을 따로 외우기보다 다음처럼 이해하는 것이 좋습니다.

```
              [ 사용자 ]
                  │
                  ▼
┌──────────────────────────┐
│          Vercel          │
│                          │
│ HTML → 화면 구조          │
│ CSS  → 디자인             │
│ JS   → 기능/fetch         │
└────────────┬─────────────┘
             │
             │ REST API
             ▼
┌──────────────────────────┐
│          Render          │
│                          │
│        FastAPI           │
│                          │
│ Data API │ Chat API      │
│ Conv API │ Summary API   │
└───────┬──────────┬───────┘
        │          │
        ▼          ▼
   Firestore    OpenAI API
        │          │
        ▼          ▼
 데이터 저장     GPT 답변
 대화 저장       AI 분석
```

그리고 가장 핵심적인 **AI 데이터 흐름**은

**Firestore 데이터 → Summary → System Prompt → GPT → 답변**

입니다.

이 흐름을 이해하면 이번 과제의 약 70~80%를 이해했다고 볼 수 있습니다.

## 14. 실제 작업은 이 순서로 하는 것을 권합니다

처음부터 웹 화면을 만들기보다 **Backend부터 하나씩 검증**하는 것이 훨씬 쉽습니다.

**① 데이터 선정 → ② Python 데이터 분석 → ③ Firestore 구축 → ④ FastAPI 기본 실행 → ⑤ CRUD API → ⑥ Swagger 테스트 → ⑦ Summary API → ⑧ GPT API → ⑨ 대화저장 → ⑩ HTML/CSS/JS → ⑪ Render → ⑫ Vercel → ⑬ README 작성**

특히 **Swagger에서 Backend가 완전히 정상 동작한 뒤 Frontend를 연결하는 방식**을 추천합니다. 그래야 오류가 발생했을 때 Backend 문제인지 JavaScript 문제인지 쉽게 구분할 수 있습니다.

과제의 선택 보너스에는 **Function Calling/MCP 또는 GPT Actions, 추가 통계·그래프, CSV/JSON 내보내기, 다크모드**까지 포함되어 있으므로 기본 기능을 완성한 후 확장하는 것이 좋습니다. M1-2.AI Agent 개발 나만의 AI 비서 구축

**다음 단계로는 ②에서 사용할 실제 주제를 먼저 정하는 것이 좋습니다.** 사용자님의 기존 작업과 연결한다면 **「AI 서비스 사용비용 분석 AI 비서」** 또는 **「제조설비 생산·품질 데이터 분석 AI 비서」**가 이 과제 구조에 잘 맞습니다. 원하시면 다음 답변에서 **“1일차~5일차 실제 실습 순서 + 폴더구조 + 각 단계에서 작성해야 할 Python/HTML 파일”**까지 이어서 구체적으로 구성해드릴 수 있습니다.
