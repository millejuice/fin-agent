# Finance AI Agent 백엔드 서버 구조 및 코드 설명

## 📋 목차
1. [전체 개요](#전체-개요)
2. [프로젝트 구조](#프로젝트-구조)
3. [주요 컴포넌트](#주요-컴포넌트)
4. [데이터 흐름](#데이터-흐름)
5. [API 엔드포인트](#api-엔드포인트)
6. [핵심 기능](#핵심-기능)

---

## 전체 개요

이 백엔드는 **FastAPI 기반의 AI 금융 분석 플랫폼**입니다. 주요 기능은 다음과 같습니다:

- 📄 **PDF 재무제표 파싱**: PDF에서 재무 지표(KPI) 자동 추출
- 📊 **금융 데이터 분석**: Yahoo Finance에서 실시간 데이터 수집
- 🤖 **AI 인사이트 생성**: 규칙 기반 및 통계적 분석으로 투자 인사이트 제공
- 💰 **밸류에이션 분석**: DCF 및 멀티플 기반 기업 가치 평가
- 📈 **성과 지표 계산**: YoY, QoQ, 마진, ROIC 등 핵심 지표 산출

---

## 프로젝트 구조

```
backend/
├── app/
│   ├── main.py              # FastAPI 애플리케이션 진입점
│   ├── config.py            # 환경변수 기반 설정 관리
│   ├── logger.py            # 로깅 시스템
│   ├── db.py                # 데이터베이스 연결 및 세션 관리
│   │
│   ├── models.py            # SQLModel 데이터베이스 모델
│   ├── schemas.py           # Pydantic 요청/응답 스키마
│   │
│   ├── services.py          # 비즈니스 로직 서비스 레이어
│   ├── parser.py            # PDF 파싱 엔진
│   │
│   ├── routes/              # API 라우트 모듈
│   │   └── finance.py       # Yahoo Finance 라우트
│   │
│   ├── analysis/            # 재무 분석 모듈
│   │   ├── enhanced.py      # 향상된 티커 분석
│   │   ├── metrics.py       # 재무 지표 계산
│   │   ├── comps.py         # 동종업계 비교
│   │   └── pipeline.py      # 분석 파이프라인
│   │
│   ├── insights/            # AI 인사이트 엔진
│   │   └── engine.py        # 규칙 기반 신호 생성
│   │
│   ├── ingest/              # 외부 데이터 수집
│   │   ├── yahoo.py         # Yahoo Finance 수집기
│   │   └── util.py          # 유틸리티
│   │
│   ├── valuation.py         # DCF 밸류에이션 로직
│   ├── yahoo.py             # Yahoo Finance 클라이언트
│   ├── analysis.py          # 기본 분석 함수들
│   └── seed.py              # 초기 데이터 시딩
│
├── app.db                   # SQLite 데이터베이스
├── uploads/                 # 업로드된 PDF 저장소
├── requirements.txt         # Python 의존성
└── run.sh                  # 서버 실행 스크립트
```

---

## 주요 컴포넌트

### 1. **Application Layer (main.py)**

**역할**: FastAPI 애플리케이션의 진입점 및 라우트 정의

**주요 기능**:
- FastAPI 앱 초기화 및 미들웨어 설정 (CORS)
- 전역 예외 처리기
- API 엔드포인트 정의 및 라우팅
- 헬스 체크 엔드포인트

**구조**:
```python
app = FastAPI(title="Finance AI Agent API")
app.add_middleware(CORSMiddleware, ...)
app.include_router(finance_router, tags=["Finance"])

@app.post("/upload")      # PDF 업로드
@app.get("/companies")    # 회사 목록
@app.get("/kpis/{id}")   # KPI 조회
@app.get("/insights/...") # 인사이트 생성
@app.post("/valuation/run") # 밸류에이션 실행
```

### 2. **Configuration (config.py)**

**역할**: 애플리케이션 설정 중앙 관리

**설정 항목**:
- API 메타데이터 (제목, 버전)
- CORS 허용 오리진
- 데이터베이스 URL
- 파일 업로드 경로 및 크기 제한
- 로그 레벨
- 외부 API 타임아웃

**예시**:
```python
class Settings:
    DATABASE_URL = "sqlite:///./app.db"
    CORS_ORIGINS = ["http://localhost:5173"]
    MAX_UPLOAD_SIZE = 10485760  # 10MB
    LOG_LEVEL = "INFO"
```

### 3. **Database Layer (db.py + models.py)**

**역할**: 데이터베이스 연결, 세션 관리, 데이터 모델 정의

**models.py - 데이터 모델**:

#### Company 모델
```python
class Company(SQLModel, table=True):
    id: int                    # 기본키
    name: str                  # 회사명
    ticker: Optional[str]      # 주식 티커 (예: AAPL)
    sector: Optional[str]      # 섹터
    industry: Optional[str]    # 업종
    currency: Optional[str]    # 통화
```

#### KPI 모델
```python
class KPI(SQLModel, table=True):
    id: int
    company_id: int            # Company 외래키
    period: str                # 기간 (예: "2024-Q4")
    freq: str                  # 빈도 ("quarterly" or "annual")
    
    # 손익계산서
    revenue: Optional[float]
    op_income: Optional[float]  # 영업이익
    net_income: Optional[float] # 순이익
    
    # 재무상태표
    total_assets: Optional[float]
    total_liabilities: Optional[float]
    equity: Optional[float]
    inventory: Optional[float]
    cash: Optional[float]
    debt: Optional[float]
    
    # 현금흐름표
    operating_cf: Optional[float]  # 영업활동현금흐름
    capex: Optional[float]         # 자본지출
    
    # 파생지표
    debt_ratio: Optional[float]   # 부채비율
    
    # 메타데이터
    meta: Optional[Dict]          # JSON 형태 추가 데이터
```

**db.py - 데이터베이스 관리**:
- SQLModel 엔진 생성 및 연결 풀 설정
- 세션 관리 (컨텍스트 매니저)
- 데이터베이스 초기화 (테이블 생성)

### 4. **Service Layer (services.py)**

**역할**: 비즈니스 로직 처리, 트랜잭션 관리

**주요 함수**:

#### `handle_upload(session, file, company, period)`
```
1. PDF 파일을 디스크에 저장
2. parser.py를 사용해 PDF에서 KPI 추출
3. Company를 생성/업데이트
4. KPI를 데이터베이스에 저장
```

#### `upsert_company(session, name, ticker)`
```
- 회사명으로 기존 회사 검색
- 없으면 생성, 있으면 티커 업데이트 (제공된 경우)
```

#### `upsert_kpi(session, company_id, period, data)`
```
- 해당 회사/기간의 KPI 검색
- 없으면 생성, 있으면 업데이트
- 부채비율 자동 계산 (total_liabilities / total_assets * 100)
```

#### `list_companies(session)`
```
- 모든 회사 목록 조회
```

#### `list_kpis_by_company(session, company_id)`
```
- 특정 회사의 모든 KPI 조회 (기간순 정렬)
```

#### `ingest_yahoo(session, ticker, period_label, ...)`
```
1. Yahoo Finance에서 재무 데이터 수집
2. Company 업서트
3. 수집된 데이터를 KPI로 변환하여 저장
```

### 5. **Parser (parser.py)**

**역할**: PDF 재무제표에서 재무 지표 자동 추출

**동작 방식**:
1. **PDF 텍스트 추출**: `pdfplumber`로 첫 8페이지 텍스트 추출
2. **헤더 매칭**: 다음 패턴으로 주요 항목 검색
   ```python
   HEADER_MAP = {
       "revenue": ["net sales", "revenue", "매출액"],
       "op_income": ["operating income", "영업이익"],
       "net_income": ["net income", "순이익"],
       "total_assets": ["total assets", "자산총계"],
       # ... 기타 항목
   }
   ```
3. **숫자 추출**: 각 항목 라인에서 첫 번째 숫자 토큰 추출
4. **정규화**: 
   - 통화 기호 제거 ($, USD)
   - 천 단위 구분자 제거 (쉼표)
   - 단위 변환 (million → 1e6, billion → 1e9, 억 → 1e8)
   - 음수 처리 (괄호 형식: (1,234) → -1234)
5. **파생 지표 계산**: 부채비율 자동 계산

**한계**:
- 표 형식 파싱 미지원 (현재는 텍스트 기반)
- 회사별 맞춤 사전 부재
- 복잡한 PDF 레이아웃 처리 제한적

### 6. **Analysis Modules (analysis/)**

#### **analysis.py** - 기본 분석 함수

**`compute_ratios(rows)`**:
- KPI 리스트를 받아 파생 지표 계산
- 반환: 각 기간별 딕셔너리 리스트
- 계산 항목:
  - `ebit_margin`: EBIT / Revenue * 100
  - `net_margin`: Net Income / Revenue * 100
  - `rev_yoy`: YoY 매출 성장률 (4분기 전 대비)
  - `rev_qoq`: QoQ 매출 성장률 (1분기 전 대비)
  - `fcf_ttm`: 최근 4분기 영업현금흐름 합계
  - `roic`: 순이익 / 총자산 * 100

**`rule_based_insights(current, prev)`**:
- 현재/이전 기간 KPI 비교
- 규칙 기반 리스크 탐지:
  - 매출 YoY -10% 이상 & 재고 YoY +10% 이상 → 수요 둔화 신호
  - 부채비율 20%p 이상 증가 → 레버리지 리스크
  - 영업CF 연속 2분기 음수 → 현금 경색

**`yoy_change(series)`, `zscore_flags(series)`, `iso_flags(series)`**:
- 통계적 이상치 탐지

**`peer_snapshot(peers)`**:
- 동종업계 피어들의 지표 집계 (평균, 표준편차)

#### **insights/engine.py** - AI 인사이트 엔진

**`rule_based_signals(row, peer)`**:
- 재무 지표와 동종업계 비교를 통한 신호 생성
- 반환: `[(title, detail, weight), ...]` 튜플 리스트
- 예시 규칙:
  - 두 자릿수 매출 성장 (YoY > 10%)
  - 업계 대비 높은 수익성 (EBIT 마진 > 피어 중앙값 + 5%p)
  - ROIC 우수성 (ROIC > 피어 중앙값 * 1.2)
  - FCF 적자 (TTM FCF < 0)
  - 매출채권 비중 과다 (Receivables/Revenue > 25%)
  - 현금전환주기 장기화 (CCC > 90일)

**`synthesize(signals)`**:
- 신호 리스트를 자연어 요약으로 변환
- 반환: `{headline, bullets, score}`

### 7. **Valuation (valuation.py)**

**역할**: DCF 및 멀티플 기반 기업 가치 평가

**주요 함수**:

#### `run_valuation(session, assumption)`

**입력 (ValuationAssumption)**:
- 회사 ID, 기간
- 성장률: 1-5년 CAGR, 6-10년 CAGR, 터미널 성장률
- 마진: 영업이익률, 세율
- 재투자율
- WACC 구성요소: 무위험수익률, ERP, 베타, 부채비용, 목표 부채비율
- 피어 멀티플: P/E, P/FCF, EV/EBIT

**처리 과정**:
1. **기본값 추론**: KPI에서 매출, OCF, CAPEX, 발행주식수, 현금, 부채 추출
2. **WACC 계산**: `WACC = E/(D+E) * CoE + D/(D+E) * CoD * (1-tax)`
3. **매출 전망**: 10년간 매출 프로젝션 (1-5년: g1, 6-10년: g2)
4. **FCF 계산**: 
   - NOPAT 기반: `FCF = NOPAT * (1 - 재투자율)`
   - OCF-CAPEX 기반: `FCF = OCF * (1+g*0.8) - CAPEX * (1+g*0.7)`
   - 보수적 접근: 두 방법 중 작은 값 선택
5. **터미널 가치**: `TV = FCF_10 * (1+g) / (WACC - g)`
6. **기업가치 (EV)**: `EV = NPV(FCF 10년) + PV(TV)`
7. **주주가치**: `Equity = EV + Cash - Debt`
8. **주당가치**: `Value per Share = Equity / Shares Outstanding`
9. **멀티플 평가**: P/E, P/FCF, EV/EBIT 적용
10. **블렌딩**: `70% DCF + 30% Multiples`
11. **Piotroski F-Score**: 9점 만점 재무 건강도 점수
12. **민감도 분석**: WACC와 터미널 성장률 변수별 주당가치 계산

**반환 (ValuationOutput)**:
```python
{
    "dcf_value_per_share": float,
    "multiples_value_per_share": float,
    "blended_value_per_share": float,
    "f_score": int (0-9),
    "notes": List[str],
    "sensitivity": List[{x: WACC, y: g, value_per_share: float}]
}
```

### 8. **Yahoo Finance Integration (yahoo.py)**

**역할**: Yahoo Finance API에서 실시간 재무 데이터 수집

**주요 함수**:

#### `fetch_yahoo_financials(ticker, use_quarterly)`
```
1. yfinance.Ticker 객체 생성
2. 재무제표 데이터프레임 조회:
   - 손익계산서: financials 또는 quarterly_financials
   - 재무상태표: balance_sheet 또는 quarterly_balance_sheet
   - 현금흐름표: cashflow 또는 quarterly_cashflow
3. 인덱스를 소문자로 정규화
4. 각 항목별 후보 키워드로 검색:
   - revenue: ["total revenue", "revenue"]
   - operating_income: ["operating income", "ebit"]
   - net_income: ["net income common stockholders"]
   - ...
5. 최신 컬럼(가장 오른쪽)에서 값 추출
6. CAPEX 절대값 처리 (Yahoo는 음수로 제공)
7. 발행주식수는 fast_info 또는 info에서 조회
8. 현금 및 부채는 재무상태표에서 추출
```

**반환**:
```python
{
    "revenue": float,
    "operating_income": float,
    "net_income": float,
    "total_assets": float,
    "total_liabilities": float,
    "inventory": float,
    "operating_cf": float,
    "capex": float,
    "shares_outstanding": float,
    "cash_and_equiv": float,
    "total_debt": float
}
```

### 9. **Routes (routes/finance.py)**

**역할**: Yahoo Finance 관련 API 엔드포인트

**엔드포인트**:

#### `GET /finance/{ticker}`
- Yahoo Finance에서 티커 정보 조회
- 주요 지표 (시가총액, PER, PBR, EPS, 배당수익률) 추출
- 규칙 기반 인사이트 생성
  - PER < 15 → 저평가
  - PBR < 1 → 자산가치 대비 저평가
  - EPS > 0 → 수익성 확보

---

## 데이터 흐름

### 시나리오 1: PDF 업로드 및 분석

```
1. 클라이언트 → POST /upload
   ├─ PDF 파일, 회사명, 기간 전송

2. main.py (upload_pdf)
   └─ services.handle_upload() 호출

3. services.py (handle_upload)
   ├─ save_pdf(): 파일 저장
   ├─ parser.parse_pdf_to_kpi(): PDF 파싱
   ├─ upsert_company(): 회사 생성/업데이트
   └─ upsert_kpi(): KPI 저장

4. parser.py (parse_pdf_to_kpi)
   ├─ pdfplumber로 텍스트 추출
   ├─ HEADER_MAP으로 항목 검색
   ├─ 숫자 추출 및 정규화
   └─ 부채비율 계산

5. 데이터베이스 저장
   └─ Company, KPI 테이블에 저장

6. 응답 반환
   └─ {"company": "...", "period": "...", "extracted": {...}}
```

### 시나리오 2: 인사이트 생성

```
1. 클라이언트 → GET /insights/{company_id}/{period}

2. main.py (get_insights)
   ├─ 해당 회사의 모든 KPI 조회 (기간순)
   ├─ 현재 기간 KPI 찾기
   ├─ 이전 기간 KPI 찾기
   └─ analysis.rule_based_insights() 호출

3. analysis.py (rule_based_insights)
   ├─ YoY 변화율 계산
   ├─ 규칙 검사:
   │   ├─ 매출 YoY 하락 & 재고 증가 → 수요 둔화
   │   ├─ 부채비율 급등 → 레버리지 리스크
   │   └─ 영업CF 연속 음수 → 현금 경색
   └─ 요약, 리스크, 워치리스트, 규칙 반환

4. 응답 반환
   └─ {
        "summary": [...],
        "risks": [...],
        "watchlist": [...],
        "rules_fired": [...]
      }
```

### 시나리오 3: 밸류에이션 실행

```
1. 클라이언트 → POST /valuation/run
   └─ ValuationAssumption 전송

2. main.py (valuation_run)
   └─ valuation.run_valuation() 호출

3. valuation.py (run_valuation)
   ├─ KPI 데이터 로드
   ├─ 기본값 추론 (매출, OCF, CAPEX 등)
   ├─ WACC 계산
   ├─ 매출 전망 (10년)
   ├─ FCF 계산 (NOPAT 기반 또는 OCF-CAPEX)
   ├─ 터미널 가치 계산
   ├─ 기업가치 계산
   ├─ 멀티플 평가
   ├─ 블렌딩 (70% DCF + 30% Multiples)
   ├─ Piotroski F-Score 계산
   └─ 민감도 분석

4. 응답 반환
   └─ ValuationOutput (주당가치, F-Score, 민감도 등)
```

### 시나리오 4: Yahoo Finance 데이터 수집

```
1. 클라이언트 → POST /ingest/yahoo
   └─ ticker, period, quarterly 파라미터

2. main.py (ingest_yahoo_api)
   └─ services.ingest_yahoo() 호출

3. services.py (ingest_yahoo)
   ├─ upsert_company(): 회사 생성/업데이트
   ├─ yahoo.fetch_yahoo_financials(): 데이터 수집
   ├─ 필드 매핑 (Yahoo → KPI 모델)
   └─ upsert_kpi(): KPI 저장

4. yahoo.py (fetch_yahoo_financials)
   ├─ yfinance.Ticker 생성
   ├─ 재무제표 데이터프레임 조회
   ├─ 항목별 검색 및 추출
   └─ 반환

5. 데이터베이스 저장

6. 응답 반환
   └─ {"company_id": ..., "kpi_id": ..., "period": ...}
```

---

## API 엔드포인트

### 파일 업로드
- **POST** `/upload`
  - PDF 재무제표 업로드 및 파싱
  - Body: `file` (PDF), `company` (string), `period` (string)

### 회사 관리
- **GET** `/companies`
  - 모든 회사 목록 조회
  - Response: `List[CompanyOut]`

### KPI 조회
- **GET** `/kpis/{company_id}`
  - 특정 회사의 모든 KPI 조회
  - Response: `List[KPIOut]`

### 인사이트
- **GET** `/insights/{company_id}/{period}`
  - 해당 기간의 AI 인사이트 생성
  - Response: `InsightOut` (summary, risks, watchlist, rules_fired)

### 밸류에이션
- **POST** `/valuation/run`
  - DCF 및 멀티플 기반 가치 평가
  - Body: `ValuationAssumption`
  - Response: `ValuationOutput`

### Yahoo Finance
- **GET** `/finance/{ticker}`
  - 티커 정보 및 인사이트 조회
  - Response: `{summary: {...}, insights: [...]}`

- **POST** `/ingest/yahoo`
  - Yahoo Finance에서 데이터 수집 및 저장
  - Query: `ticker`, `period`, `quarterly`, `name` (optional)

### 분석
- **GET** `/finance/analysis/{ticker}`
  - 향상된 티커 분석
  - Query: `quarterly` (bool)

### 헬스 체크
- **GET** `/health`
  - 서버 상태 확인

---

## 핵심 기능 상세

### 1. PDF 파싱 엔진

**장점**:
- 다국어 지원 (영어, 한국어)
- 다양한 숫자 형식 처리 (천 단위 구분자, 단위, 음수)
- 유연한 헤더 매칭 (정규표현식)

**제한사항**:
- 텍스트 기반 파싱 (표 구조 인식 불가)
- 레이아웃에 민감
- 회사별 맞춤 사전 필요

**개선 방향**:
- Camelot/Tabula 등 표 파싱 라이브러리 통합
- 회사별 사전 구축
- ML 기반 항목 인식

### 2. 인사이트 엔진

**규칙 기반 접근**:
- 명시적 규칙으로 설명 가능한 결과
- 도메인 전문가 지식 반영 용이
- 디버깅 및 개선이 쉬움

**통계적 접근**:
- Z-score 기반 이상치 탐지
- Isolation Forest 기반 이상치 탐지
- 동종업계 비교

**개선 방향**:
- ML 모델 통합 (LSTM, Transformer)
- 자연어 생성 (GPT 등)
- 시간적 패턴 학습

### 3. 밸류에이션 엔진

**DCF 모델**:
- 10년 현금흐름 전망
- 터미널 가치 계산 (Gordon Growth)
- WACC 기반 할인율

**멀티플 모델**:
- P/E, P/FCF, EV/EBIT 적용
- 동종업계 평균 멀티플 활용

**Piotroski F-Score**:
- 재무 건강도 0-9점 평가
- 수익성, 레버리지, 효율성 종합

**민감도 분석**:
- WACC 변수별 영향 분석
- 터미널 성장률 변수별 영향 분석

---

## 기술 스택

### 프레임워크
- **FastAPI**: 고성능 비동기 웹 프레임워크
- **SQLModel**: 타입 안전 ORM (SQLAlchemy + Pydantic)
- **Pydantic**: 데이터 검증 및 스키마

### 데이터베이스
- **SQLite**: 개발/프로덕션 (PostgreSQL 등으로 교체 가능)

### 데이터 수집
- **yfinance**: Yahoo Finance API 클라이언트
- **pdfplumber**: PDF 파싱

### 분석
- **NumPy**: 수치 계산
- **Pandas**: 데이터 조작
- **scikit-learn**: 이상치 탐지 (IsolationForest)

### 기타
- **uvicorn**: ASGI 서버
- **python-multipart**: 파일 업로드 처리

---

## 보안 및 모범 사례

✅ **구현됨**:
- 입력 검증 (Pydantic)
- 파일 크기 제한
- 에러 핸들링 (예외 정보 누출 방지)
- CORS 설정
- 로깅 시스템

⚠️ **개선 필요**:
- 인증/인가 (JWT)
- Rate Limiting
- SQL Injection 방지 (SQLModel이 자동 처리하지만 검증 필요)
- 파일 업로드 검증 (PDF만 허용)

---

## 확장 가능성

### 단기 개선
1. PostgreSQL 마이그레이션
2. Redis 캐싱 (Yahoo Finance 응답)
3. 비동기 작업 큐 (Celery) - 긴 작업 배경 처리
4. 데이터베이스 마이그레이션 (Alembic)

### 장기 개선
1. ML 모델 통합 (예측, 분류)
2. 실시간 스트리밍 (WebSocket)
3. 멀티테넌트 지원
4. 마이크로서비스 분리
5. Kubernetes 배포

---

## 실행 방법

```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 또는 run.sh 사용
./run.sh
```

**API 문서**: `http://localhost:8000/docs`

---

## 요약

이 백엔드는 **프로덕션 레벨의 구조**를 갖춘 금융 분석 플랫폼입니다:

✅ **계층화된 아키텍처**: Route → Service → Model
✅ **관심사 분리**: 각 모듈이 명확한 책임
✅ **에러 처리**: 전역 예외 핸들러 및 세부 에러 처리
✅ **로깅**: 구조화된 로깅 시스템
✅ **설정 관리**: 환경변수 기반 설정
✅ **타입 안전성**: Type hints 및 Pydantic 검증
✅ **확장성**: 모듈화된 구조로 쉬운 확장

**핵심 강점**:
- PDF에서 자동으로 재무 데이터 추출
- 실시간 외부 데이터 수집 (Yahoo Finance)
- 규칙 기반 + 통계적 AI 인사이트
- 전문적인 DCF 밸류에이션
- 프로덕션 준비된 코드 품질

