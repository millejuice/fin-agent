# app/ingest/yahoo.py
import yfinance as yf
import pandas as pd
from .util import to_period, to_unit_usdm

def fetch_yahoo_full(ticker: str, freq="Q"):
    t = yf.Ticker(ticker)
    # 분/연 재무제표
    fin = (t.quarterly_financials if freq == "Q" else t.financials) or pd.DataFrame()
    bal = (t.quarterly_balance_sheet if freq == "Q" else t.balance_sheet) or pd.DataFrame()
    cf  = (t.quarterly_cashflow if freq == "Q" else t.cashflow) or pd.DataFrame()
    info = t.info or {}

    # index: 계정, columns: dates → 컬럼별(period)로 재구성
    def colmap(df):
        if df is None or df.empty: return {}
        out = {}
        for col in df.columns:
            period = to_period(col)              # "2025-Q2" 등
            out.setdefault(period, {})
            out[period].update({k: float(df.loc[k, col]) for k in df.index if pd.notna(df.loc[k, col])})
        return out

    merged = {}
    for period, d in colmap(fin).items():  merged.setdefault(period, {}).update(d)
    for period, d in colmap(bal).items():  merged.setdefault(period, {}).update(d)
    for period, d in colmap(cf).items():   merged.setdefault(period, {}).update(d)

    # 스케일 통일(USDm) & 키 매핑
    data = []
    for period, m in merged.items():
        row = {
          "period": period, "freq": ("Q" if "Q" in period else "A"),
          "revenue": to_unit_usdm(m.get("Total Revenue") or m.get("Revenue")),
          "gross_profit": to_unit_usdm(m.get("Gross Profit")),
          "ebit": to_unit_usdm(m.get("Ebit") or m.get("Operating Income")),
          "ebitda": to_unit_usdm(m.get("Ebitda")),
          "net_income": to_unit_usdm(m.get("Net Income")),
          "total_assets": to_unit_usdm(m.get("Total Assets")),
          "total_liabilities": to_unit_usdm(m.get("Total Liab") or m.get("Total Liabilities")),
          "equity": to_unit_usdm(m.get("Total Stockholder Equity") or m.get("Total Equity Gross Minority Interest")),
          "oper_cf": to_unit_usdm(m.get("Total Cash From Operating Activities")),
          "invest_cf": to_unit_usdm(m.get("Total Cashflows From Investing Activities")),
          "finance_cf": to_unit_usdm(m.get("Total Cash From Financing Activities")),
          "capex": to_unit_usdm(m.get("Capital Expenditures")),
          "inventory": to_unit_usdm(m.get("Inventory")),
          "receivables": to_unit_usdm(m.get("Net Receivables")),
          "payables": to_unit_usdm(m.get("Accounts Payable")),
          "cash": to_unit_usdm(m.get("Cash") or m.get("Cash And Cash Equivalents")),
          "debt": to_unit_usdm(m.get("Short Long Term Debt") or 0) + to_unit_usdm(m.get("Long Term Debt") or 0),
          "meta": {"source":"yahoo", "currency": info.get("currency") or "USD", "unit":"USDm"}
        }
        data.append(row)

    return info, sorted(data, key=lambda x: x["period"])
