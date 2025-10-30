# backend/app/schemas.py
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class CompanyOut(BaseModel):
    id: int
    name: str

class KPIOut(BaseModel):
    id: int
    company_id: int
    period: str
    revenue: Optional[float]
    op_income: Optional[float]
    net_income: Optional[float]
    total_assets: Optional[float]
    total_liabilities: Optional[float]
    operating_cf: Optional[float]
    inventory: Optional[float]
    debt_ratio: Optional[float]
    capex: Optional[float] = 0
    shares_outstanding: Optional[float] = 0
    cash_and_equiv: Optional[float] = 0
    total_debt: Optional[float] = 0

class InsightOut(BaseModel):
    summary: List[str]
    risks: List[str]
    watchlist: List[str]
    rules_fired: List[str]

class UploadResult(BaseModel):
    company: str
    period: str
    extracted: Dict[str, Any]

# ▼ 밸류에이션
class ValuationAssumption(BaseModel):
    company_id:   int
    period:       str

    # 성장/마진/세율/투자
    base_revenue: Optional[float] = None   # 없으면 해당 period revenue 사용
    base_op_margin: float = 0.15           # 영업이익률
    tax_rate: float = 0.21
    revenue_cagr_years_1_5: float = 0.08   # 1~5년 매출 CAGR
    revenue_cagr_years_6_10: float = 0.04  # 6~10년
    terminal_growth: float = 0.02          # 영구성장률(g)
    reinvestment_rate: float = 0.25        # FCF = NOPAT - Reinvestment, 또는 OCF-CAPEX 방식 병행

    # 현금흐름/자본비용
    use_ocf_capex: bool = True             # True면 OCF-CAPEX 방식, False면 NOPAT-재투자
    capex_override: Optional[float] = None # 최신 CAPEX 입력(없으면 KPI.capex)
    ocf_override: Optional[float] = None   # 최신 OCF 입력(없으면 KPI.operating_cf)

    # WACC
    rf: float = 0.04                       # 무위험수익률
    erp: float = 0.05                      # 주식위험프리미엄
    beta: float = 1.0
    pre_tax_cost_of_debt: float = 0.05
    target_debt_ratio: float = 0.20        # D / (D+E)

    # 멀티플 비교
    peer_pe: Optional[float] = 20.0
    peer_pfcf: Optional[float] = 18.0
    peer_ev_ebit: Optional[float] = 14.0

    # 발행주식수/현금/부채 (없으면 KPI에서)
    shares_outstanding: Optional[float] = None
    cash_and_equiv: Optional[float] = None
    total_debt: Optional[float] = None

class SensitivityCell(BaseModel):
    x: float
    y: float
    value_per_share: float

class ValuationOutput(BaseModel):
    dcf_value_per_share: float
    multiples_value_per_share: float
    blended_value_per_share: float = Field(..., description="예: 70% DCF + 30% 멀티플")
    f_score: int
    notes: List[str]
    sensitivity: List[SensitivityCell]
