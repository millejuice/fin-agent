"""
Finance routes for Yahoo Finance integration.
"""
from fastapi import APIRouter, HTTPException
from app.logger import get_logger
import yfinance as yf

logger = get_logger("routes.finance")
router = APIRouter()


@router.get("/finance/{ticker}")
async def get_finance_data(ticker: str):
    """
    Get financial data and insights for a stock ticker from Yahoo Finance.
    
    - **ticker**: Stock ticker symbol (e.g., AAPL, MSFT, TSLA)
    
    Returns summary metrics and AI-generated insights.
    """
    try:
        logger.info(f"Fetching finance data for ticker: {ticker}")
        stock = yf.Ticker(ticker.upper())
        
        # Get company info with timeout handling
        try:
            info = stock.info
        except Exception as e:
            logger.error(f"Failed to fetch info for {ticker}: {e}")
            raise HTTPException(
                status_code=404,
                detail=f"Could not fetch data for ticker {ticker}. Please verify the ticker symbol."
            )
        
        if not info or not info.get("longName"):
            raise HTTPException(
                status_code=404,
                detail=f"No data found for ticker {ticker}"
            )
        
        # Extract key metrics
        summary = {
            "ticker": ticker.upper(),
            "name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "marketCap": info.get("marketCap"),
            "peRatio": info.get("trailingPE") or info.get("forwardPE"),
            "pbRatio": info.get("priceToBook"),
            "eps": info.get("trailingEps") or info.get("forwardEps"),
            "dividendYield": info.get("dividendYield"),
        }
        
        # Generate insights based on valuation metrics
        insights = []
        pe_ratio = summary.get("peRatio")
        pb_ratio = summary.get("pbRatio")
        eps = summary.get("eps")
        
        if pe_ratio:
            if pe_ratio < 15:
                insights.append(f"PER이 {pe_ratio:.2f}로 동종업계 대비 저평가로 보입니다.")
            elif pe_ratio > 25:
                insights.append(f"PER이 {pe_ratio:.2f}로 동종업계 대비 고평가일 수 있습니다.")
            else:
                insights.append(f"PER이 {pe_ratio:.2f}로 적정 수준입니다.")
        
        if pb_ratio:
            if pb_ratio < 1:
                insights.append("PBR < 1 → 자산가치 대비 저평가일 수 있습니다.")
            elif pb_ratio > 3:
                insights.append(f"PBR이 {pb_ratio:.2f}로 높은 수준입니다.")
        
        if eps:
            if eps > 0:
                insights.append(f"EPS가 {eps:.2f}로 양수 → 수익성이 확보된 기업입니다.")
            else:
                insights.append("EPS가 음수 → 손실 상태입니다.")
        
        if not insights:
            insights.append("추가적인 분석이 필요합니다.")
        
        logger.info(f"Successfully retrieved finance data for {ticker}")
        return {
            "summary": summary,
            "insights": insights
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching finance data for {ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch finance data: {str(e)}"
        )
