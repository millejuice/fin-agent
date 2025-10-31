from .metrics import (
    ttm, growth_rate, margin, roic, invested_capital, ccc as cash_conversion_cycle, days_ratio
)
from .enhanced import analyze_ticker, generate_enhanced_insights
# rules
from .rules import rule_based_insights
# compute_ratios가 pipeline.py에 있다면 아래 import 유지
try:
    from .pipeline import compute_ratios, peer_snapshot
except Exception:   # 아직 없으면 무시
    compute_ratios = None  # 혹은 적절한 더미
    peer_snapshot = None

__all__ = [
    # metrics
    "ttm", "growth_rate", "margin", "roic", "invested_capital",
    "cash_conversion_cycle", "days_ratio",
    # enhanced
    "analyze_ticker", "generate_enhanced_insights",
    # rules
    "rule_based_insights",
    # pipeline
    "compute_ratios", "peer_snapshot",
]