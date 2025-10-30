# app/insights/engine.py
from typing import Dict, List, Tuple

def rule_based_signals(row: Dict, peer: Dict) -> List[Tuple[str, str, float]]:
    """(title, detail, weight) 반환. weight는 중요도 스코어."""
    out = []

    # 성장/수익성
    if (row.get("rev_yoy") or 0) > 0.1:
        out.append(("두 자릿수 매출 성장", f"YoY {row['rev_yoy']*100:.1f}%", 0.7))
    if (row.get("ebit_margin") or 0) > (peer.get("ebit_margin",{}).get("median",0) + 0.05):
        out.append(("업계 대비 높은 수익성", "EBIT 마진이 업계 중앙값을 ~5%p 이상 상회", 0.8))
    if row.get("roic") and peer.get("roic"):
        peer_med = peer["roic"]["median"]
        if row["roic"] > peer_med*1.2:
            out.append(("자본효율 우수", f"ROIC {row['roic']*100:.1f}% (업계중앙 {peer_med*100:.1f}%)", 0.9))

    # 현금흐름/퀄리티
    if (row.get("fcf_ttm") or 0) < 0:
        out.append(("FCF 적자", "최근 4분기 누적 FCF가 음수", 0.6))

    # 재고/매출 인식 리스크 시그널(기본)
    if (row.get("receivables") and row.get("revenue")):
        ar_ratio = row["receivables"]/row["revenue"]
        if ar_ratio > 0.25:
            out.append(("매출채권 비중 과다", f"Receivables/Revenue ≈ {ar_ratio:.2f}", 0.5))

    # 운전자본 악화
    if row.get("ccc") and row["ccc"] > 90:  # 분기기준 대략 90일 초과
        out.append(("현금전환주기 장기화", f"CCC ≈ {row['ccc']:.0f}일", 0.6))

    return out

def synthesize(summary_items: List[Tuple[str,str,float]]) -> Dict:
    summary_items.sort(key=lambda x: x[2], reverse=True)
    headline = summary_items[0][0] if summary_items else "특이사항 없음"
    bullets = [f"• {t}: {d}" for (t,d,_) in summary_items[:6]]
    score = min(100, int(sum(w*100 for *_,w in summary_items[:6]) / 6)) if summary_items else 50
    return {"headline": headline, "bullets": bullets, "score": score}
