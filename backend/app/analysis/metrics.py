# app/analysis/metrics.py
from typing import List, Dict, Optional
import math

def ttm(series: List[Optional[float]]) -> Optional[float]:
    vals = [v for v in series[-4:] if v is not None]
    return sum(vals) if len(vals) == 4 else None

def growth_rate(curr: Optional[float], prev: Optional[float]) -> Optional[float]:
    if curr is None or prev is None or prev == 0: return None
    return (curr/prev) - 1.0

def margin(numer: Optional[float], denom: Optional[float]) -> Optional[float]:
    if numer is None or denom in (None, 0): return None
    return numer/denom

def roic(ebit: Optional[float], tax_rate: float, invested_capital: Optional[float]) -> Optional[float]:
    if ebit is None or invested_capital in (None, 0): return None
    nopat = ebit * (1 - tax_rate)
    return nopat / invested_capital

def invested_capital(total_assets, non_interest_liab):
    if total_assets is None or non_interest_liab is None: return None
    return total_assets - non_interest_liab

def ccc(dso, dio, dpo):
    if None in (dso, dio, dpo): return None
    return dso + dio - dpo

def days_ratio(balance, flow_per_period, days=90):
    # e.g., DSO = AR / revenue * days
    if balance is None or flow_per_period in (None, 0): return None
    return balance / flow_per_period * days
