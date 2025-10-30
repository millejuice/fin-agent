from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from .db import init_db, get_session
from sqlmodel import Session, select
from . import services
from .schemas import CompanyOut, KPIOut, UploadResult, InsightOut, ValuationAssumption, ValuationOutput
from .models import Company, KPI
from .valuation import run_valuation
from fastapi import FastAPI, Depends, Query
from .db import get_session
from . import services
import yfinance as yf
from fastapi import FastAPI
from .analysis.enhanced import analyze_ticker


app = FastAPI(title="Finance AI Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

@app.post("/upload", response_model=UploadResult)
def upload_pdf(
    file: UploadFile = File(...),
    company: str = Form(...),
    period: str = Form(...),
    session: Session = Depends(get_session)
):
    return services.handle_upload(session, file, company, period)

@app.get("/companies", response_model=List[CompanyOut])
def get_companies(session: Session = Depends(get_session)):
    rows = services.list_companies(session)
    return [{"id": r.id, "name": r.name} for r in rows]

@app.get("/kpis/{company_id}", response_model=List[KPIOut])
def get_kpis(company_id: int, session: Session = Depends(get_session)):
    rows = services.list_kpis_by_company(session, company_id)
    return [r.dict() for r in rows]

@app.post("/valuation/run", response_model=ValuationOutput)
def valuation_run(asm: ValuationAssumption, session: Session = Depends(get_session)):
    try:
        return run_valuation(session, asm)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/insights/{company_id}/{period}", response_model=InsightOut)
def get_insights(company_id: int, period: str, session: Session = Depends(get_session)):
    # 현재/이전 분기 비교
    rows = session.exec(select(KPI).where(KPI.company_id==company_id).order_by(KPI.period)).all()
    target = next((r for r in rows if r.period == period), None)
    if not target:
        return {"summary": ["데이터 없음"], "risks": [], "watchlist": [], "rules_fired": []}
    # 직전 분기
    prev = None
    for i, r in enumerate(rows):
        if r.period == period and i>0:
            prev = rows[i-1]
            break
    cur = target.dict()
    prv = prev.dict() if prev else {}
    # 간단 YoY 대용으로 '직전 4개 전'이 없을 수 있어, 데모에선 직전 분기로 비교 예시
    # (필요시 날짜 파서 도입 권장)
    cur["revenue_yoy"] = None
    cur["inventory_yoy"] = None
    if prev:
        def pct(a,b): 
            if b in (None,0) or a is None: return None
            return (a-b)/abs(b)*100.0
        cur["revenue_yoy"] = pct(cur.get("revenue"), prv.get("revenue"))
        cur["inventory_yoy"] = pct(cur.get("inventory"), prv.get("inventory"))

    out = rule_based_insights(cur, prv if prv else {})
    return out

@app.post("/ingest/yahoo")
def ingest_yahoo_api(
    ticker: str = Query(..., description="예: AAPL"),
    period: str = Query(..., description="예: 2024 또는 2024-Q4"),
    quarterly: bool = Query(False, description="True면 분기, False면 연간"),
    name: str | None = Query(None, description="회사명(옵션)"),
    session = Depends(get_session)
):
    return services.ingest_yahoo(session, ticker=ticker, period_label=period, quarterly=quarterly, company_name=name)
@app.get("/finance/{ticker}")
def get_finance(ticker: str):
    stock = yf.Ticker(ticker)
    info = stock.info

    return {
        "summary": {
            "ticker": ticker,
            "name": info.get("longName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "marketCap": info.get("marketCap"),
            "peRatio": info.get("trailingPE"),
            "pbRatio": info.get("priceToBook"),
            "eps": info.get("trailingEps"),
            "dividendYield": info.get("dividendYield"),
        },
        "insights": [
            f"{ticker}의 PER은 {info.get('trailingPE')}로 동종업계 대비 {'저평가' if info.get('trailingPE', 0) < 15 else '고평가'}로 보입니다.",
            f"EPS는 {info.get('trailingEps')}로 최근 실적 기반의 이익 수준을 반영합니다.",
        ]
    }

@app.get("/finance/analysis/{ticker}")
def finance_analysis(ticker: str, quarterly: bool = True):
    try:
        return analyze_ticker(ticker, quarterly=quarterly)
    except Exception as e:
        return {"error": str(e)}
