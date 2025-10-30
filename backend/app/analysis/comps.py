# app/analysis/comps.py
import statistics as stats

def peer_snapshot(companies: list[dict], metric_keys=("rev_ttm","ebit_margin","roic","fcf_ttm")):
    peers = [c for c in companies if all(k in (c or {}) for k in metric_keys)]
    if not peers: return {}
    agg = {}
    for k in metric_keys:
        vals = [p.get(k) for p in peers if p.get(k) is not None]
        if not vals: continue
        agg[k] = {"mean": sum(vals)/len(vals), "median": stats.median(vals)}
    return agg

def z_score(value, mean, std):
    if None in (value, mean) or std in (None, 0): return None
    return (value-mean)/std
