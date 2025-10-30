# backend/app/valuation.py
from __future__ import annotations
from typing import List, Dict, Tuple
from sqlmodel import Session, select
import math

from .models import KPI
from .schemas import ValuationAssumption, ValuationOutput, SensitivityCell

def _get_latest_kpi(session: Session, company_id: int, period: str) -> KPI | None:
    rows = session.exec(select(KPI).where(KPI.company_id==company_id).order_by(KPI.period)).all()
    target = next((r for r in rows if r.period == period), None)
    return target

def _infer_base_values(kpi: KPI, asm: ValuationAssumption) -> Tuple[float,float,float,float,float]:
    # revenue, ocf, capex, shares, cash, debt
    revenue = asm.base_revenue if asm.base_revenue is not None else (kpi.revenue or 0)
    ocf = asm.ocf_override if asm.ocf_override is not None else (kpi.operating_cf or 0)
    capex = asm.capex_override if asm.capex_override is not None else (kpi.capex or 0)
    shares = asm.shares_outstanding if asm.shares_outstanding is not None else (kpi.shares_outstanding or 0)
    cash = asm.cash_and_equiv if asm.cash_and_equiv is not None else (kpi.cash_and_equiv or 0)
    debt = asm.total_debt if asm.total_debt is not None else (kpi.total_debt or 0)
    return revenue, ocf, capex, shares, cash, debt

def _wacc(asm: ValuationAssumption) -> float:
    # CoE = rf + beta * ERP
    coe = asm.rf + asm.beta * asm.erp
    # CoD after tax = pre_tax_cost_of_debt * (1 - tax_rate)
    cod = asm.pre_tax_cost_of_debt * (1 - asm.tax_rate)
    d = asm.target_debt_ratio
    e = 1 - d
    return e * coe + d * cod

def _project_revenue(rev0: float, g1: float, g2: float) -> List[float]:
    # 10년 구간: 1~5년 g1, 6~10년 g2
    rev = []
    cur = rev0
    for year in range(1, 11):
        g = g1 if year <= 5 else g2
        cur = cur * (1 + g)
        rev.append(cur)
    return rev

def _ebit_from_margin(revenue: float, margin: float) -> float:
    return revenue * margin

def _nopat(ebit: float, tax_rate: float) -> float:
    return ebit * (1 - tax_rate)

def _fcf_series_from_nopat(nopat_list: List[float], asm: ValuationAssumption) -> List[float]:
    # 간단화: Reinvestment = ReinvestmentRate * Revenue 증가분 근사 대신,
    # NOPAT 기준 재투자율 적용 (보수적)
    fcf = [np - (np * asm.reinvestment_rate) for np in nopat_list]
    return fcf

def _fcf_series_from_ocf_capex(ocf0: float, capex0: float, g1: float, g2: float) -> List[float]:
    # OCF, CAPEX도 성장률에 유사하게 연동(보수적)
    fcf = []
    ocf = ocf0
    capex = capex0
    for year in range(1, 11):
        g = g1 if year <= 5 else g2
        ocf = ocf * (1 + g*0.8)     # OCF는 매출 성장의 0.8배 탄력으로 성장 가정(보수)
        capex = capex * (1 + max(g,0)*0.7)  # CAPEX는 성장 시 일부 증가
        fcf.append(ocf - capex)
    return fcf

def _terminal_value(last_cashflow: float, wacc: float, g: float) -> float:
    if wacc <= g:
        g = wacc - 0.005  # 안정화
    return last_cashflow * (1 + g) / (wacc - g)

def _npv(cashflows: List[float], wacc: float) -> float:
    return sum(cf / ((1 + wacc) ** (i+1)) for i, cf in enumerate(cashflows))

def _enterprise_to_equity(ev: float, cash: float, debt: float) -> float:
    return ev + cash * 1.0 - debt * 1.0

def _piotroski_f_score(history: List[KPI]) -> int:
    # 9점 만점. 가용 데이터만 사용(없으면 해당 항목 skip).
    score = 0
    if len(history) < 2:
        return score
    cur, prev = history[-1], history[-2]

    def gt(a: float|None, b: float|None) -> bool:
        return (a is not None and b is not None and a > b)

    # 수익성: ROA 증가(순이익/자산), CFO>0, ROA>0, CFO>NI
    roa_cur = (cur.net_income or 0) / max(cur.total_assets or 1, 1)
    roa_prev = (prev.net_income or 0) / max(prev.total_assets or 1, 1)
    if gt(roa_cur, roa_prev): score += 1
    if (cur.operating_cf or 0) > 0: score += 1
    if roa_cur > 0: score += 1
    if (cur.operating_cf or 0) > (cur.net_income or 0): score += 1

    # 레버리지/유동성/발행: 부채비율 감소, 유동성 개선(여기선 단순: 부채/자산 감소), 신주발행X(데이터 없으면 skip)
    cur_leverage = (cur.total_liabilities or 0) / max(cur.total_assets or 1, 1)
    prev_leverage = (prev.total_liabilities or 0) / max(prev.total_assets or 1, 1)
    if cur_leverage < prev_leverage: score += 1

    # 효율성: 매출총이익률/자산회전율 증가(데이터 한계 → 대체지표)
    # 여기선 영업이익률과 매출/자산 회전율로 근사
    cur_margin = (cur.op_income or 0) / max(cur.revenue or 1, 1)
    prev_margin = (prev.op_income or 0) / max(prev.revenue or 1, 1)
    if cur_margin > prev_margin: score += 1
    cur_turnover = (cur.revenue or 0) / max(cur.total_assets or 1, 1)
    prev_turnover = (prev.revenue or 0) / max(prev.total_assets or 1, 1)
    if cur_turnover > prev_turnover: score += 1

    # 신주발행(발행주식수 증가) 체크
    if (cur.shares_outstanding or 0) and (prev.shares_outstanding or 0):
        if (cur.shares_outstanding or 0) <= (prev.shares_outstanding or 0):
            score += 1

    return score

def run_valuation(session: Session, asm: ValuationAssumption) -> ValuationOutput:
    # 데이터 로드
    rows = session.exec(select(KPI).where(KPI.company_id==asm.company_id).order_by(KPI.period)).all()
    if not rows:
        raise ValueError("No KPI history")
    kpi = next((r for r in rows if r.period == asm.period), rows[-1])

    base_rev, ocf0, capex0, shares, cash, debt = _infer_base_values(kpi, asm)
    if base_rev <= 0:
        raise ValueError("Base revenue is missing or zero. Provide base_revenue.")
    if shares <= 0:
        # 주당가치 계산 위해 필요. 없으면 가정치 요구
        raise ValueError("Shares outstanding missing. Provide shares_outstanding in assumptions or KPI.")

    w = _wacc(asm)

    # 매출/마진 → NOPAT 기반 FCF
    rev_path = _project_revenue(base_rev, asm.revenue_cagr_years_1_5, asm.revenue_cagr_years_6_10)
    ebit_path = [_ebit_from_margin(r, asm.base_op_margin) for r in rev_path]
    nopat_path = [_nopat(e, asm.tax_rate) for e in ebit_path]
    fcf_nopat = _fcf_series_from_nopat(nopat_path, asm)

    # OCF-CAPEX 기반 FCF (둘 중 보수적인 값 채택)
    if asm.use_ocf_capex:
        fcf_ocf = _fcf_series_from_ocf_capex(ocf0, capex0, asm.revenue_cagr_years_1_5, asm.revenue_cagr_years_6_10)
        fcf_series = [min(a, b) for a, b in zip(fcf_nopat, fcf_ocf)]
        note_flow = "FCF = min(NOPAT-based, OCF-CAPEX-based) per year (conservative)."
    else:
        fcf_series = fcf_nopat
        note_flow = "FCF = NOPAT-based with reinvestment rate."

    # 터미널
    tv = _terminal_value(fcf_series[-1], w, asm.terminal_growth)

    # EV (기업가치) = NPV(FCF 10Y) + PV(TV)
    ev = _npv(fcf_series, w) + tv / ((1 + w) ** 10)

    # Equity value
    equity_value = _enterprise_to_equity(ev, cash, debt)
    dcf_per_share = equity_value / shares

    # 멀티플(보수적 평균)
    # P/E → 순이익, P/FCF → OCF-CAPEX, EV/EBIT → EBIT
    cur_ebit = ebit_path[0]
    cur_fcfe = (ocf0 - capex0) if (ocf0 or capex0) else (nopat_path[0])  # 대체
    cur_ni = (kpi.net_income or 0) if (kpi.net_income is not None) else (nopat_path[0] * (1-0.0))

    # EV/EBIT로 EV 추정
    ev_peers = []
    if asm.peer_ev_ebit and cur_ebit > 0:
        ev_peers.append(asm.peer_ev_ebit * cur_ebit)
    if not ev_peers and cur_ebit <= 0:
        # EBIT 음수일 경우 멀티플 무의미 → P/FCF만 사용
        pass

    eq_peers = []
    if asm.peer_pe and cur_ni > 0:
        eq_peers.append(asm.peer_pe * cur_ni)
    if asm.peer_pfcf and cur_fcfe > 0:
        eq_peers.append(asm.peer_pfcf * cur_fcfe)

    # EV 멀티플 있으면 Equity 전환
    eq_from_ev = None
    if ev_peers:
        ev_m = sum(ev_peers)/len(ev_peers)
        eq_from_ev = _enterprise_to_equity(ev_m, cash, debt)

    candidates = []
    if eq_from_ev is not None:
        candidates.append(eq_from_ev)
    if eq_peers:
        candidates.append(sum(eq_peers)/len(eq_peers))

    multiples_per_share = (sum(candidates)/len(candidates))/shares if candidates else dcf_per_share

    # 블렌드
    blended = 0.7 * dcf_per_share + 0.3 * multiples_per_share

    # F-score
    fscore = _piotroski_f_score(rows)

    # 민감도 (WACC vs Terminal g)
    xs = [max(0.06, w-0.02), max(0.05, w-0.01), w, w+0.01, w+0.02]
    ys = [max(0.0, asm.terminal_growth-0.01), asm.terminal_growth, asm.terminal_growth+0.01]
    sens: List[SensitivityCell] = []
    for xx in xs:
        for yy in ys:
            tv_ = _terminal_value(fcf_series[-1], xx, yy)
            ev_ = _npv(fcf_series, xx) + tv_ / ((1 + xx) ** 10)
            eq_ = _enterprise_to_equity(ev_, cash, debt)
            sens.append(SensitivityCell(x=round(xx,4), y=round(yy,4), value_per_share=eq_/shares))

    notes = [
        f"WACC={round(w,4)}, g={asm.terminal_growth}",
        note_flow,
        "Blended = 70% DCF + 30% Multiples.",
        f"Inputs: margin={asm.base_op_margin}, tax={asm.tax_rate}, reinvest={asm.reinvestment_rate}",
        "Peer multiples used when meaningful/positive.",
    ]

    return ValuationOutput(
        dcf_value_per_share=dcf_per_share,
        multiples_value_per_share=multiples_per_share,
        blended_value_per_share=blended,
        f_score=fscore,
        notes=notes,
        sensitivity=sens,
    )
