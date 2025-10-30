# app/analysis/pipeline.py
from typing import List, Dict, Optional, Any
from .metrics import ttm, growth_rate, margin, roic, invested_capital, ccc, days_ratio

def compute_ratios(sorted_kpis: List[Dict]) -> List[Dict]:
    """기간 오름차순 KPI 배열 → 파생지표/TTM/YoY/QoQ 채워 넣은 동일 길이 배열 반환"""
    out = []
    for i, k in enumerate(sorted_kpis):
        prev_q = sorted_kpis[i-1] if i-1 >= 0 else None
        prev_y = sorted_kpis[i-4] if i-4 >= 0 else None

        rev = k.get("revenue"); ebit = k.get("ebit"); net = k.get("net_income")
        gp  = k.get("gross_profit"); assets=k.get("total_assets"); liab=k.get("total_liabilities")
        equity=k.get("equity"); ocf=k.get("oper_cf"); capex=k.get("capex")
        inv=k.get("inventory"); ar=k.get("receivables"); ap=k.get("payables")

        # 마진
        gross_margin = margin(gp, rev)
        ebit_margin  = margin(ebit, rev)
        net_margin   = margin(net, rev)

        # 성장률
        rev_qoq = growth_rate(rev, prev_q.get("revenue") if prev_q else None)
        rev_yoy = growth_rate(rev, prev_y.get("revenue") if prev_y else None)

        # TTM 지표
        rev_ttm = ttm([r.get("revenue") for r in sorted_kpis[:i+1]])
        net_ttm = ttm([r.get("net_income") for r in sorted_kpis[:i+1]])
        ocf_ttm = ttm([r.get("oper_cf") for r in sorted_kpis[:i+1]])
        capex_ttm = ttm([r.get("capex") for r in sorted_kpis[:i+1]])
        fcf_ttm = (ocf_ttm - capex_ttm) if (ocf_ttm is not None and capex_ttm is not None) else None

        # ROIC
        non_interest_liab = (liab or 0) - (k.get("debt") or 0)
        ic = invested_capital(assets, non_interest_liab)
        roic_v = roic(ebit, tax_rate=0.21, invested_capital=ic)  # 기본 21% 가정 (미국 법인세)

        # 운전자본 / CCC
        # COGS 근사: revenue - gross_profit
        cogs = (rev - gp) if (rev is not None and gp is not None) else None
        dso = days_ratio(ar, rev)
        dio = days_ratio(inv, cogs)
        dpo = days_ratio(ap, cogs)
        ccc_v = ccc(dso, dio, dpo)

        out.append({
          **k,
          "gross_margin": gross_margin, "ebit_margin": ebit_margin, "net_margin": net_margin,
          "rev_qoq": rev_qoq, "rev_yoy": rev_yoy,
          "rev_ttm": rev_ttm, "net_ttm": net_ttm, "fcf_ttm": fcf_ttm,
          "roic": roic_v, "ccc": ccc_v,
        })
    return out


def peer_snapshot(peers: List[Optional[Dict]]) -> Dict[str, Any]:
  """
  Aggregate peer metrics (list of latest ratio dicts) into basic statistics.
  Returns a dict with mean/std/count for selected numeric keys.
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
      if v is None:
        continue
      try:
        values[k].append(float(v))
      except Exception:
        continue

  for k in numeric_keys:
    arr = values[k]
    if arr:
      mean = sum(arr) / len(arr)
      # population std
      var = sum((x - mean) ** 2 for x in arr) / len(arr)
      std = var ** 0.5
      stats[f"{k}_mean"] = mean
      stats[f"{k}_std"] = std
    else:
      stats[f"{k}_mean"] = None
      stats[f"{k}_std"] = None

  return stats
