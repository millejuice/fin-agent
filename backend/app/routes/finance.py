# app/routes/finance.py
from fastapi import APIRouter
import yfinance as yf

router = APIRouter()

@router.get("/finance/{ticker}")
def get_finance_data(ticker: str):
    stock = yf.Ticker(ticker)
    info = stock.info

    # 주요 지표 추출
    summary = {
        "ticker": ticker,
        "name": info.get("shortName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "marketCap": info.get("marketCap"),
        "peRatio": info.get("forwardPE"),
        "pbRatio": info.get("priceToBook"),
        "eps": info.get("trailingEps"),
        "dividendYield": info.get("dividendYield"),
    }

    # 단순 규칙 기반 인사이트
    insights = []
    if summary["peRatio"] and summary["peRatio"] < 15:
        insights.append("PER이 낮아 저평가 가능성이 있습니다.")
    if summary["pbRatio"] and summary["pbRatio"] < 1:
        insights.append("PBR < 1 → 자산가치 대비 저평가일 수 있습니다.")
    if summary["eps"] and summary["eps"] > 0:
        insights.append("EPS가 양수 → 수익성이 확보된 기업입니다.")
    if not insights:
        insights.append("추가적인 분석이 필요합니다.")

    return {"summary": summary, "insights": insights}
