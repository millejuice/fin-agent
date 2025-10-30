# app/analysis/enhanced.py
from functools import lru_cache
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import yfinance as yf

def _pct(x): 
    try: return float(x) if x is not None else None
    except: return None

def _pct_change(series, periods=4):  # QoQ 기본 4, 연환산/연속 분기 전제
    s = pd.to_numeric(series, errors="coerce")
    return (s.pct_change(periods=periods) * 100).round(2)

@lru_cache(maxsize=256)
def analyze_ticker(ticker: str, quarterly: bool = True):
    t = ticker.upper().strip()
    y = yf.Ticker(t)

    # 기본 메타
    info = y.info or {}
    name = info.get("shortName") or info.get("longName") or t
    sector = info.get("sector")
    industry = info.get("industry")
    market_cap = info.get("marketCap")
    currency = info.get("currency", "USD")

    # 재무제표 (quarterly 기준)
    is_ = (y.quarterly_financials if quarterly else y.financials).T  # IS
    bs_ = (y.quarterly_balance_sheet if quarterly else y.balance_sheet).T
    cf_ = (y.quarterly_cashflow if quarterly else y.cashflow).T

    # 컬럼 표준 키(없으면 NaN)
    col = lambda df, k: pd.to_numeric(df.get(k), errors="coerce")

    rev = col(is_, "Total Revenue")                 # 매출
    gp  = col(is_, "Gross Profit")
    op  = col(is_, "Operating Income")
    ni  = col(is_, "Net Income")
    cfo = col(cf_, "Total Cash From Operating Activities")
    inv = col(bs_, "Inventory")
    ar  = col(bs_, "Net Receivables")
    ap  = col(bs_, "Accounts Payable")
    ta  = col(bs_, "Total Assets")
    te  = col(bs_, "Total Stockholder Equity")

    # 파생 지표
    gm  = (gp / rev * 100).round(2)
    opm = (op / rev * 100).round(2)
    npm = (ni / rev * 100).round(2)
    asset_turnover = (rev / ta).round(2)
    equity_multiplier = (ta / te).round(2)
    roe_dupont = (npm/100 * asset_turnover * equity_multiplier * 100).round(2)

    # 간이 CCC (보수적 계산)
    # 매출원가 없으면 GP로 근사
    cogs = pd.to_numeric(is_.get("Cost Of Revenue") or (rev - gp), errors="coerce")
    days_inv = (inv / (cogs/365)).replace([np.inf, -np.inf], np.nan).round(1)
    days_ar  = (ar  / (rev/365)).replace([np.inf, -np.inf], np.nan).round(1)
    days_ap  = (ap  / (cogs/365)).replace([np.inf, -np.inf], np.nan).round(1)
    ccc = (days_inv + days_ar - days_ap).round(1)

    # 성장률 (QoQ/YoY)
    qoq_rev = _pct_change(rev, 1)   # 직전 분기 대비
    yoy_rev = _pct_change(rev, 4)   # 전년 동기 대비
    yoy_op  = _pct_change(op, 4)
    yoy_ni  = _pct_change(ni, 4)

    # 멀티플(현재가 기반)
    price = pd.to_numeric(info.get("currentPrice") or info.get("regularMarketPrice"), errors="coerce")
    shares = pd.to_numeric(info.get("sharesOutstanding"), errors="coerce")
    ttm_eps = pd.to_numeric(info.get("trailingEps"), errors="coerce")
    ttm_pe = (price/ttm_eps).round(2) if price and ttm_eps and ttm_eps != 0 else None
    pbr = pd.to_numeric(info.get("priceToBook"), errors="coerce")
    div_yield = pd.to_numeric(info.get("dividendYield"), errors="coerce")

    # 동종업계 벤치마크(간단 버전: info의 sector/industry 평균을 못 믿으니 rule만)
    # 현업스럽게 보이려면 별도 peer-set 수집/캐시가 필요. (다음 단계)
    benchmarks = {
        "pe_median": None, "pbr_median": None, "npm_median": None, "roe_median": None
    }

    # 신호(rule-based)
    flags = []
    if yoy_rev.dropna().size and yoy_rev.iloc[-1] < 0:
        flags.append({"type":"warning","msg":"매출 YoY 감소"})
    if (opm.dropna().size and npm.dropna().size and
        (opm.iloc[-1] < 10 or npm.iloc[-1] < 5)):
        flags.append({"type":"watch","msg":"수익성(마진) 취약 구간"})
    if ccc.dropna().size and ccc.iloc[-1] > 100:
        flags.append({"type":"watch","msg":"현금전환주기(CCC) 장기화"})

    # 확신도(최근 8~12개 분기 가용률)
    frames = [rev, gp, op, ni]
    available = np.mean([f.notna().sum()/max(len(f),1) for f in frames])
    confidence = round(float(available)*100, 0)

    return {
        "meta": {
            "ticker": t, "name": name, "sector": sector, "industry": industry,
            "marketCap": market_cap, "currency": currency,
            "asOf": datetime.now(timezone.utc).isoformat()
        },
        "multiples": {
            "pe": _pct(ttm_pe), "pbr": _pct(pbr), "eps": _pct(ttm_eps),
            "dividendYield": _pct(div_yield)
        },
        "trend": {
            "rev": rev.dropna().tail(12).to_dict(),
            "op": op.dropna().tail(12).to_dict(),
            "ni": ni.dropna().tail(12).to_dict(),
            "gm": gm.dropna().tail(12).to_dict(),
            "opm": opm.dropna().tail(12).to_dict(),
            "npm": npm.dropna().tail(12).to_dict(),
            "roeDupont": roe_dupont.dropna().tail(12).to_dict(),
            "ccc": ccc.dropna().tail(12).to_dict(),
            "qoq_rev": qoq_rev.dropna().tail(8).to_dict(),
            "yoy_rev": yoy_rev.dropna().tail(8).to_dict()
        },
        "benchmarks": benchmarks,   # 추후 peer-set로 채움
        "flags": flags,
        "confidence": confidence,
    }

# backend/app/analysis/enhanced.py  (파일 맨 아래에 추가)

def generate_enhanced_insights(ticker: str, quarterly: bool = True):
    """
    프론트엔드/서비스 레이어에서 기대하는 이름.
    내부적으로 analyze_ticker를 호출해 가볍게 요약/신호를 포맷팅합니다.
    """
    d = analyze_ticker(ticker, quarterly=quarterly)

    meta = d.get("meta", {})
    mult = d.get("multiples", {})
    trend = d.get("trend", {})
    flags = d.get("flags", [])
    confidence = d.get("confidence")

    # 간단 요약(필요시 더 발전)
    summary = []
    if trend.get("yoy_rev"):
        last_yoy = list(trend["yoy_rev"].values())[-1]
        summary.append(f"매출 YoY {last_yoy}%")
    if mult.get("pe") is not None:
        summary.append(f"PER {mult['pe']}")
    if mult.get("pbr") is not None:
        summary.append(f"PBR {mult['pbr']}")

    return {
        "meta": meta,
        "multiples": mult,
        "trend": trend,
        "flags": flags,
        "confidence": confidence,
        "summary": summary,
    }
