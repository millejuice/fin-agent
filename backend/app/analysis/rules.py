from typing import Dict, Any, List

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
