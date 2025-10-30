# app/yahoo.py
from __future__ import annotations
import pandas as pd
import yfinance as yf
from typing import Dict, Optional

def _pick(df: pd.DataFrame, candidates: list[str]) -> Optional[pd.Series]:
    if df is None or df.empty:
        return None
    idx = [i.lower() for i in df.index]
    for key in candidates:
        k = key.lower()
        if k in idx:
            return df.iloc[idx.index(k)]
    # 완전 일치가 없으면 포함 검색(유연)
    for key in candidates:
        for i, row_name in enumerate(idx):
            if key.lower() in row_name:
                return df.iloc[i]
    return None

def _col_latest(series: Optional[pd.Series]) -> Optional[float]:
    if series is None or series.empty:
        return None
    # 최신 열(마지막 컬럼 또는 가장 최근 날짜열)
    s = series.dropna()
    if s.empty:
        return None
    # yfinance는 컬럼이 기간(날짜/연도) — 가장 오른쪽이 최신인 경우가 많음
    return float(s.iloc[0]) if hasattr(s, "iloc") else float(s)

def _normalize_capex(x: Optional[float]) -> Optional[float]:
    # Yahoo는 CapEx가 음수로 나오는 경우가 흔함(유출). 내부적으로는 절대값으로 사용하도록 정규화.
    if x is None:
        return None
    return abs(x)

def fetch_yahoo_financials(ticker: str, use_quarterly: bool = False) -> Dict[str, Optional[float]]:
    t = yf.Ticker(ticker)

    # 연간/분기 선택
    is_df  = t.quarterly_financials if use_quarterly else t.financials            # 손익계산서
    bs_df  = t.quarterly_balance_sheet if use_quarterly else t.balance_sheet      # 재무상태표
    cf_df  = t.quarterly_cashflow if use_quarterly else t.cashflow                # 현금흐름표

    # 행 인덱스를 소문자로 변환(매칭 편의)
    def lower_index(df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
        if df is None or df.empty:
            return df
        df = df.copy()
        df.index = [str(i).strip().lower() for i in df.index]
        return df

    is_df = lower_index(is_df)
    bs_df = lower_index(bs_df)
    cf_df = lower_index(cf_df)

    # 각 항목 후보(라벨은 야후 쪽 표기 변동에 대비해서 여러 개 넣음)
    revenue            = _col_latest(_pick(is_df, ["total revenue", "revenue"]))
    operating_income   = _col_latest(_pick(is_df, ["operating income", "operating income or loss", "ebit"]))
    net_income         = _col_latest(_pick(is_df, ["net income common stockholders", "net income"]))
    total_assets       = _col_latest(_pick(bs_df, ["total assets"]))
    total_liabilities  = _col_latest(_pick(bs_df, ["total liabilities net minority interest", "total liabilities"]))
    inventory          = _col_latest(_pick(bs_df, ["inventory"]))
    operating_cf       = _col_latest(_pick(cf_df, ["operating cash flow", "cash flow from operations"]))
    capex_raw          = _col_latest(_pick(cf_df, ["capital expenditure", "capital expenditures"]))
    capex              = _normalize_capex(capex_raw)

    # 발행주식수/현금/부채
    info = (t.fast_info or {})  # fast_info가 더 빠름
    shares_outstanding = None
    try:
        # fast_info 우선, 없으면 info
        shares_outstanding = float(info.get("shares_outstanding") or t.info.get("sharesOutstanding") or 0) or None
    except Exception:
        shares_outstanding = None

    cash_and_equiv = None
    try:
        # balance sheet에서 Cash & Cash Equivalents 항목이 더 정확
        cash_and_equiv = _col_latest(_pick(bs_df, ["cash and cash equivalents", "cash and short term investments", "cash"]))
    except Exception:
        pass

    total_debt = None
    try:
        # 총부채가 있으면 우선 사용. 없으면 장단기부채 합산 시도
        total_debt = _col_latest(_pick(bs_df, ["total debt"]))
        if total_debt is None:
            s_debt = _col_latest(_pick(bs_df, ["short long term debt", "short term debt", "short long-term debt"]))
            l_debt = _col_latest(_pick(bs_df, ["long term debt", "long-term debt"]))
            if s_debt or l_debt:
                total_debt = (s_debt or 0) + (l_debt or 0)
    except Exception:
        pass

    return {
        "revenue": revenue,
        "operating_income": operating_income,
        "net_income": net_income,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "inventory": inventory,
        "operating_cf": operating_cf,
        "capex": capex,
        "shares_outstanding": shares_outstanding,
        "cash_and_equiv": cash_and_equiv,
        "total_debt": total_debt,
    }
