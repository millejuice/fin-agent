# backend/app/analysis.py
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.ensemble import IsolationForest

def yoy_change(series: List[float]) -> List[float|None]:
    out = []
    for i, v in enumerate(series):
        if i < 4 or series[i-4] in (None, 0):
            out.append(None)
        else:
            out.append((v - series[i-4]) / abs(series[i-4]) * 100.0)
    return out

def zscore_flags(series: List[float], thr: float = 2.5) -> List[bool]:
    arr = np.array([x if x is not None else np.nan for x in series], dtype=float)
    mu, sd = np.nanmean(arr), np.nanstd(arr)
    flags = []
    for x in arr:
        if np.isnan(x) or sd == 0:
            flags.append(False)
        else:
            flags.append(abs((x - mu) / sd) >= thr)
    return flags

def iso_flags(series: List[float]) -> List[bool]:
    vals = np.array([x if x is not None else 0.0 for x in series], dtype=float).reshape(-1, 1)
    model = IsolationForest(contamination=0.15, random_state=42)
    pred = model.fit_predict(vals)
    return [p == -1 for p in pred]

def rule_based_insights(current: Dict[str, Any], prev: Dict[str, Any]) -> Dict[str, List[str]]:
    summary, risks, watch, fired = [], [], [], []
    # 예시 규칙
    if current.get("revenue_yoy") is not None and current["revenue_yoy"] <= -10 \
       and current.get("inventory_yoy") is not None and current["inventory_yoy"] >= 10:
        risks.append("수요 둔화: 매출 YoY 하락 & 재고 YoY 상승 동시 발생")
        fired.append("R1")

    if current.get("debt_ratio") is not None and prev.get("debt_ratio") is not None:
        if (current["debt_ratio"] - prev["debt_ratio"]) >= 20:
            risks.append("부채비율 급등(20%p↑): 재무 레버리지 리스크")
            fired.append("R2")

    if current.get("operating_cf") is not None and prev.get("operating_cf") is not None:
        if current["operating_cf"] < 0 and prev["operating_cf"] < 0:
            risks.append("영업CF 연속 2분기 음수: 현금 경색 우려")
            fired.append("R3")

    # 요약/워치리스트 템플릿
    summary.append("핵심: 최근 분기 KPI와 YoY/QoQ를 자동 산출했습니다.")
    summary.append("이상치 탐지는 z-score/IsolationForest로 표기했습니다.")
    watch.append("매출 회복 추세 여부 확인")
    watch.append("재고 회전율 모니터링")
    watch.append("현금흐름 개선 계획 점검")
    return {"summary": summary, "risks": risks, "watchlist": watch, "rules_fired": fired}


def compute_ratios(rows: List[object]) -> List[Dict[str, Any]]:
    """
    Convert a list of KPI-like objects (ORM rows) into a list of dicts with derived ratios.

    Expected input: rows ordered chronologically (old -> new). Each row should have attributes
    like period, revenue, op_income (EBIT), net_income, total_assets, total_liabilities,
    operating_cf, inventory.

    Returns list of dicts with added keys such as rev_yoy, rev_qoq, ebit, ebit_margin, net_margin,
    fcf_ttm (sum of last 4 operating_cf), and basic fields copied through.
    """
    out: List[Dict[str, Any]] = []
    # copy numeric series for YoY/QoQ
    revenues: List[Optional[float]] = []
    ops: List[Optional[float]] = []
    nets: List[Optional[float]] = []
    op_cfs: List[Optional[float]] = []

    for r in rows:
        revenues.append(getattr(r, "revenue", None))
        ops.append(getattr(r, "op_income", None))
        nets.append(getattr(r, "net_income", None))
        op_cfs.append(getattr(r, "operating_cf", None))

    # compute yoy (4-period) and qoq (1-period)
    def pct_change(curr: Optional[float], prev: Optional[float]) -> Optional[float]:
        if curr is None or prev in (None, 0):
            return None
        try:
            return (curr - prev) / abs(prev) * 100.0
        except Exception:
            return None

    n = len(rows)
    for i, r in enumerate(rows):
        rec: Dict[str, Any] = {}
        rec["period"] = getattr(r, "period", None)
        revenue = revenues[i]
        ebit = ops[i]
        net = nets[i]
        total_assets = getattr(r, "total_assets", None)
        total_liabilities = getattr(r, "total_liabilities", None)
        operating_cf = op_cfs[i]

        rec.update({
            "revenue": revenue,
            "ebit": ebit,
            "net_income": net,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "operating_cf": operating_cf,
            "inventory": getattr(r, "inventory", None),
        })

        # margins
        rec["ebit_margin"] = (ebit / revenue * 100.0) if (ebit is not None and revenue) else None
        rec["net_margin"] = (net / revenue * 100.0) if (net is not None and revenue) else None

        # yoy (4 periods) and qoq
        rec["rev_qoq"] = pct_change(revenue, revenues[i-1]) if i-1 >= 0 else None
        rec["rev_yoy"] = pct_change(revenue, revenues[i-4]) if i-4 >= 0 else None

        # fcf_ttm: sum of last 4 operating cash flows (if available)
        try:
            last4 = [x for x in op_cfs[max(0, i-3): i+1] if x is not None]
            rec["fcf_ttm"] = sum(last4) if last4 else None
        except Exception:
            rec["fcf_ttm"] = None

        # simple ROIC approximation if data exists
        try:
            if net is not None and total_assets:
                rec["roic"] = (net / total_assets) * 100.0
            else:
                rec["roic"] = None
        except Exception:
            rec["roic"] = None

        out.append(rec)

    return out


def peer_snapshot(peers: List[Optional[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Aggregate peer metrics (list of latest_ratios dicts) into simple statistics.

    Returns a dict with mean/std/count for numeric keys.
    """
    numeric_keys = [
        "revenue", "ebit", "net_income", "ebit_margin", "net_margin", "roic", "fcf_ttm"
    ]
    stats: Dict[str, Any] = {"count": 0}
    values: Dict[str, List[float]] = {k: [] for k in numeric_keys}

    for p in peers:
        if not p:
            continue
        stats["count"] += 1
        for k in numeric_keys:
            v = p.get(k)
            if v is not None:
                try:
                    values[k].append(float(v))
                except Exception:
                    continue

    for k in numeric_keys:
        arr = np.array(values[k]) if values[k] else np.array([])
        if arr.size:
            stats[f"{k}_mean"] = float(np.mean(arr))
            stats[f"{k}_std"] = float(np.std(arr))
        else:
            stats[f"{k}_mean"] = None
            stats[f"{k}_std"] = None

    return stats
