# app/ingest/util.py
import pandas as pd

def to_period(col) -> str:
    # pandas.Timestamp → "YYYY-Qn" or "YYYY"
    if isinstance(col, (pd.Timestamp, )):
        q = (col.month-1)//3 + 1
        return f"{col.year}-Q{q}"
    s = str(col)
    # 날짜형 문자열도 대응
    try:
        dt = pd.to_datetime(s, errors="coerce")
        if pd.notna(dt):
            q = (dt.month-1)//3 + 1
            return f"{dt.year}-Q{q}"
    except: pass
    return s

def to_unit_usdm(x):
    if x is None: return None
    return float(x) / 1_000_000.0
