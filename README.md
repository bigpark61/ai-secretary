# 제조 데이터 분석 AI 비서

제공된 제조 공정 CSV를 Firestore에 저장하고, 데이터를 관리·요약하며 OpenAI API로 자연어 질문에 답하는 기본 웹 애플리케이션입니다.

## 기능

- 제조 데이터 CSV 300건을 Firestore `data` 컬렉션에 멱등성 있게 적재
- 데이터 생성·목록·수정·삭제 API와 웹 화면
- 평균·최솟값·최댓값 및 RecordID 표본 순서 비교 요약
- 요약을 시스템 프롬프트에 넣는 AI 채팅과 Firestore 자동 대화 저장
- 대화 기록 목록·불러오기·삭제
- FastAPI Swagger UI (`/docs`)

> 제공된 CSV에는 날짜/시간 컬럼이 없습니다. 따라서 통계에서 날짜나 기간을 임의로 만들지 않습니다. `trend`는 RecordID가 있는 원본 표본의 앞·뒤 20% 비교이며 시간 추세를 뜻하지 않습니다.

## 기술 스택

- Backend: Python, FastAPI, Firebase Admin SDK / Cloud Firestore
- AI: OpenAI Chat Completions API (`gpt-4o-mini` 기본)
- Frontend: HTML, CSS, Vanilla JavaScript
- Deployment: Render (API), Vercel (정적 웹)

## 로컬 실행

Python 3.10 이상을 권장합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

`.env`의 Firebase 서비스 계정 설정과 `OPENAI_API_KEY`를 채운 뒤 다음처럼 실행합니다.

```powershell
python -m uvicorn app.main:app --reload --env-file .env
```

웹 앱은 `http://127.0.0.1:8000`, Swagger는 `http://127.0.0.1:8000/docs`에서 확인합니다. Firestore 자격 증명은 코드나 저장소에 추가하지 마세요. `FIREBASE_SERVICE_ACCOUNT_JSON`에 서비스 계정 JSON 전체를 환경 변수로 지정하는 방법도 지원합니다.

## Firestore 데이터 구조

- `data/{id}`: 제조 지표, `source_record_id`, `created_at`, `updated_at`
- `conversations/{id}`: 제목, `{role, content}` 메시지 배열, 생성/수정 시각

Firebase Console에서 Firestore Database를 만들고, 사용하는 서비스 계정에 최소한의 Firestore 읽기/쓰기 권한을 부여하세요. 제공된 CSV 기본 경로는 `data/manufacturing_analysis_300_enhanced.csv`입니다.

```powershell
python -m scripts.import_csv
```

다른 CSV는 다음처럼 지정합니다.

```powershell
python -m scripts.import_csv --csv "C:\data\manufacturing.csv"
```

같은 `RecordID`는 `csv-{RecordID}` 문서 ID로 저장/갱신되어 재실행해도 중복 생성되지 않습니다.

## API

| Method | Path | 설명 |
| --- | --- | --- |
| `POST` | `/api/data` | 데이터 생성 |
| `GET` | `/api/data` | 전체 목록 |
| `PUT` | `/api/data/{id}` | 데이터 수정 |
| `DELETE` | `/api/data/{id}` | 데이터 삭제 |
| `GET` | `/api/data/summary` | 요약 통계 |
| `POST` | `/api/conversations` | 대화 저장 |
| `GET` | `/api/conversations` | 대화 목록 |
| `GET` | `/api/conversations/{id}` | 전체 메시지 조회 |
| `DELETE` | `/api/conversations/{id}` | 대화 삭제 |
| `POST` | `/api/chat` | 요약 컨텍스트 기반 AI 대화 및 자동 저장 |

## 환경 변수

| 이름 | 용도 |
| --- | --- |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Firebase 서비스 계정 JSON 문자열 |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | 서비스 계정 JSON 파일 경로 (JSON 문자열 대신 사용) |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `OPENAI_MODEL` | 모델명, 기본값 `gpt-4o-mini` |
| `ALLOWED_ORIGINS` | 쉼표로 구분한 CORS 허용 웹 도메인 |
| `API_BASE_URL` | Vercel 프로젝트 환경 변수. Render API 기본 URL |

키가 없거나 AI 설정이 빠졌을 때 임의의 성공 응답을 반환하지 않고 설정 오류를 보여줍니다. 무료 Render 서비스는 첫 요청에 콜드 스타트 지연이 있을 수 있습니다.

## 배포

### Render

저장소 루트를 Render Web Service로 배포하고 Build Command에 `pip install -r requirements.txt`, Start Command에 `uvicorn app.main:app --host 0.0.0.0 --port $PORT`를 설정합니다. `FIREBASE_SERVICE_ACCOUNT_JSON`, `OPENAI_API_KEY`, `ALLOWED_ORIGINS`를 Render 환경 변수에 등록한 뒤 `/docs`와 `/api/health`를 확인합니다. 서비스 계정 키 파일을 저장소에 올리지 마세요.

### Vercel

저장소 루트를 Vercel 프로젝트로 연결합니다. 포함된 `vercel.json`이 정적 출력 디렉터리를 `web`으로 지정합니다. Vercel 프로젝트 환경 변수 `API_BASE_URL`에 Render API의 origin(예: `https://your-service.onrender.com`)을 설정하고, Render의 `ALLOWED_ORIGINS`에 배포된 Vercel origin을 추가합니다. `/api/config` 함수가 이 URL을 웹 클라이언트에 전달합니다.

## 테스트

```powershell
python -m pytest -q
```

## 배포 URL 및 제출 스크린샷

- 프론트엔드: 배포 후 URL 입력
- 백엔드 API: 배포 후 Render URL 입력
- Swagger UI: `https://<Render URL>/docs`
- 스크린샷: 데이터 요약이 보이는 채팅, 데이터 생성/삭제, 대화 불러오기 화면을 배포 후 첨부
