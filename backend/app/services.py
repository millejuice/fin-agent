# backend/app/services.py
import os
from typing import Dict, List
from sqlmodel import Session, select
from .models import Company, KPI
from .parser import parse_pdf_to_kpi
from sqlmodel import select, Session
from .models import Company, KPI
from .yahoo import fetch_yahoo_financials

from .analysis import compute_ratios
from .analysis import peer_snapshot
from app.insights.engine import rule_based_signals, synthesize

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
os.makedirs(DATA_DIR, exist_ok=True)

def save_pdf(file) -> str:
    path = os.path.join(DATA_DIR, file.filename)
    with open(path, "wb") as f:
        f.write(file.file.read())
    return path

def upsert_company(session: Session, name: str) -> Company:
    c = session.exec(select(Company).where(Company.name == name)).first()
    if not c:
        c = Company(name=name)
        session.add(c)
        session.commit()
        session.refresh(c)
    return c

def upsert_kpi(session: Session, company_id: int, period: str, data: Dict) -> KPI:
    row = session.exec(select(KPI).where((KPI.company_id==company_id) & (KPI.period==period))).first()
    if not row:
        row = KPI(company_id=company_id, period=period)
    for k, v in data.items():
        if hasattr(row, k):
            setattr(row, k, float(v))
    # 부채비율 보정
    if (row.total_assets or 0) and (row.total_liabilities or 0):
        row.debt_ratio = (row.total_liabilities / row.total_assets) * 100.0

    session.add(row)
    session.commit()
    session.refresh(row)
    return row

def list_companies(session: Session) -> List[Company]:
    return session.exec(select(Company)).all()

def list_kpis_by_company(session: Session, company_id: int) -> List[KPI]:
    return session.exec(select(KPI).where(KPI.company_id==company_id).order_by(KPI.period)).all()

def handle_upload(session: Session, file, company: str, period: str) -> Dict:
    path = save_pdf(file)
    extracted = parse_pdf_to_kpi(path)
    c = upsert_company(session, company)
    upsert_kpi(session, c.id, period, extracted)
    return {"company": company, "period": period, "extracted": extracted}

def upsert_company(session: Session, name: str, ticker: str | None = None) -> Company:
    c = session.exec(select(Company).where(Company.name == name)).first()
    if c:
        if ticker and c.ticker != ticker:
            c.ticker = ticker
            session.add(c)
            session.commit()
            session.refresh(c)
        return c
    c = Company(name=name, ticker=ticker)
    session.add(c)
    session.commit()
    session.refresh(c)
    return c

def ingest_yahoo(session: Session, ticker: str, period_label: str, *, quarterly=False, company_name: str | None = None):
    """Yahoo에서 가져온 최신 값으로 KPI 한 건 생성/갱신."""
    # 회사 업서트
    name = company_name or ticker.upper()
    company = upsert_company(session, name=name, ticker=ticker.upper())

    data = fetch_yahoo_financials(ticker, use_quarterly=quarterly)

    # 기존 동일 period 있으면 업데이트
    kpi = session.exec(
        select(KPI).where(KPI.company_id == company.id, KPI.period == period_label)
    ).first()
    if not kpi:
        kpi = KPI(company_id=company.id, period=period_label)

    for k, v in data.items():
        setattr(kpi, k, v)

    # 파생 지표(부채비율 등)
    if (kpi.total_liabilities is not None) and (kpi.total_assets is not None) and kpi.total_assets != 0:
        kpi.debt_ratio = float(kpi.total_liabilities) / float(kpi.total_assets) * 100.0

    session.add(kpi)
    session.commit()
    session.refresh(kpi)
    return {"company_id": company.id, "kpi_id": kpi.id, "period": kpi.period}


def make_insight(session, company_id: int, period: str) -> dict:
    # 1) 해당 회사 최근 N분기 KPI 조회 & 계산
    rows = get_kpis_for_company(session, company_id, limit=12)  # 오름차순
    rows_calc = compute_ratios(rows)
    row = next((r for r in rows_calc if r["period"] == period), rows_calc[-1])

    # 2) 동종업계 peer 집합 생성(간단 버전: 같은 sector/industry)
    company = session.get(Company, company_id)
    peer_companies = get_companies_by_industry(session, company.industry)
    peer_last = [ latest_ratios_for_company(session, c.id) for c in peer_companies ]
    peer_stats = peer_snapshot([p for p in peer_last if p])

    # 3) 규칙기반 + 통계적 시그널
    signals = rule_based_signals(row, peer_stats)

    # 4) 자연어 요약
    nlg = synthesize(signals)

    return {
      "headline": nlg["headline"],
      "summary": nlg["bullets"],
      "score": nlg["score"],
      "evidence": {
         "period": period,
         "kpi": {k: row.get(k) for k in ("revenue","ebit","net_income","gross_margin","ebit_margin","net_margin","roic","fcf_ttm","ccc","rev_yoy","rev_qoq")},
         "peers": peer_stats
      },
      "trace": signals   # [(rule-title, detail, weight)] → 디버깅/설명가능성
    }