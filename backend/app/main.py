"""
FastAPI application entry point.
Professional structure with proper error handling, logging, and route organization.
"""
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
from sqlmodel import Session, select

from app.config import settings
from app.logger import setup_logging, get_logger
from app.db import init_db, get_session
from app import services
from app.schemas import (
    CompanyOut, 
    KPIOut, 
    UploadResult, 
    InsightOut, 
    ValuationAssumption, 
    ValuationOutput
)
from app.models import Company, KPI
from app.valuation import run_valuation
from app.analysis import rule_based_insights
from app.routes.finance import router as finance_router
from app.analysis.enhanced import analyze_ticker

# Setup logging
logger = setup_logging(settings.LOG_LEVEL)

# Initialize FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unhandled exceptions gracefully."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.LOG_LEVEL == "DEBUG" else "An unexpected error occurred"
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


# Startup event
@app.on_event("startup")
def on_startup():
    """Initialize application on startup."""
    try:
        init_db()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "version": settings.API_VERSION}


# Include routers
app.include_router(finance_router, tags=["Finance"])


# ============================================================================
# File Upload Routes
# ============================================================================

@app.post("/upload", response_model=UploadResult, tags=["Upload"])
async def upload_pdf(
    file: UploadFile = File(...),
    company: str = Form(...),
    period: str = Form(...),
    session: Session = Depends(get_session)
):
    """
    Upload and parse a financial report PDF.
    
    - **file**: PDF file to upload
    - **company**: Company name
    - **period**: Period identifier (e.g., "2024-Q4")
    """
    logger.info(f"Received upload request: {file.filename} for {company} - {period}")
    return services.handle_upload(session, file, company, period)


# ============================================================================
# Company Routes
# ============================================================================

@app.get("/companies", response_model=List[CompanyOut], tags=["Companies"])
async def get_companies(session: Session = Depends(get_session)):
    """
    Get all companies in the database.
    
    Returns a list of all companies with their IDs and names.
    """
    try:
        companies = services.list_companies(session)
        return [
            {"id": c.id, "name": c.name, "ticker": getattr(c, "ticker", None)} 
            for c in companies
        ]
    except Exception as e:
        logger.error(f"Error fetching companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# KPI Routes
# ============================================================================

@app.get("/kpis/{company_id}", response_model=List[KPIOut], tags=["KPIs"])
async def get_kpis(company_id: int, session: Session = Depends(get_session)):
    """
    Get all KPIs for a specific company.
    
    - **company_id**: Company ID
    """
    try:
        kpis = services.list_kpis_by_company(session, company_id)
        if not kpis:
            raise HTTPException(
                status_code=404,
                detail=f"No KPIs found for company ID {company_id}"
            )
        return [kpi.dict() for kpi in kpis]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching KPIs for company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Insights Routes
# ============================================================================

@app.get("/insights/{company_id}/{period}", response_model=InsightOut, tags=["Insights"])
async def get_insights(
    company_id: int, 
    period: str, 
    session: Session = Depends(get_session)
):
    """
    Generate AI-powered insights for a company's financial period.
    
    - **company_id**: Company ID
    - **period**: Period identifier (e.g., "2024-Q4")
    
    Returns insights including summary, risks, watchlist items, and triggered rules.
    """
    try:
        # Fetch KPIs for the company, ordered by period
        kpis = session.exec(
            select(KPI)
            .where(KPI.company_id == company_id)
            .order_by(KPI.period)
        ).all()
        
        if not kpis:
            raise HTTPException(
                status_code=404,
                detail=f"No KPIs found for company ID {company_id}"
            )
        
        # Find target period and previous period
        target_kpi = next((k for k in kpis if k.period == period), None)
        if not target_kpi:
            return {
                "summary": ["데이터 없음"],
                "risks": [],
                "watchlist": [],
                "rules_fired": []
            }
        
        # Find previous period for comparison
        prev_kpi = None
        target_index = next(
            (i for i, k in enumerate(kpis) if k.period == period),
            None
        )
        if target_index is not None and target_index > 0:
            prev_kpi = kpis[target_index - 1]
        
        # Convert to dictionaries
        current_dict = target_kpi.dict()
        prev_dict = prev_kpi.dict() if prev_kpi else {}
        
        # Calculate YoY changes (using previous period as proxy)
        if prev_kpi:
            def calculate_pct_change(current_val, prev_val):
                if prev_val in (None, 0) or current_val is None:
                    return None
                try:
                    return ((current_val - prev_val) / abs(prev_val)) * 100.0
                except (ZeroDivisionError, TypeError):
                    return None
            
            current_dict["revenue_yoy"] = calculate_pct_change(
                current_dict.get("revenue"),
                prev_dict.get("revenue")
            )
            current_dict["inventory_yoy"] = calculate_pct_change(
                current_dict.get("inventory"),
                prev_dict.get("inventory")
            )
        else:
            current_dict["revenue_yoy"] = None
            current_dict["inventory_yoy"] = None
        
        # Generate insights using rule-based engine
        insights = rule_based_insights(current_dict, prev_dict)
        
        logger.info(
            f"Generated insights for company {company_id}, period {period}: "
            f"{len(insights.get('summary', []))} summary points, "
            f"{len(insights.get('risks', []))} risks"
        )
        
        return insights
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating insights: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")


# ============================================================================
# Valuation Routes
# ============================================================================

@app.post("/valuation/run", response_model=ValuationOutput, tags=["Valuation"])
async def valuation_run(
    assumption: ValuationAssumption,
    session: Session = Depends(get_session)
):
    """
    Run DCF and multiples-based valuation analysis.
    
    - **assumption**: Valuation assumptions including growth rates, margins, WACC, etc.
    
    Returns comprehensive valuation analysis with DCF, multiples, and sensitivity analysis.
    """
    try:
        logger.info(
            f"Running valuation for company {assumption.company_id}, "
            f"period {assumption.period}"
        )
        return run_valuation(session, assumption)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error running valuation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Valuation failed: {str(e)}")


# ============================================================================
# Yahoo Finance Ingestion Routes
# ============================================================================

@app.post("/ingest/yahoo", tags=["Ingestion"])
async def ingest_yahoo_api(
    ticker: str = Query(..., description="Stock ticker symbol, e.g., AAPL"),
    period: str = Query(..., description="Period label, e.g., 2024 or 2024-Q4"),
    quarterly: bool = Query(False, description="Use quarterly data if True, annual if False"),
    name: str | None = Query(None, description="Optional company name override"),
    session: Session = Depends(get_session)
):
    """
    Ingest financial data from Yahoo Finance for a given ticker.
    
    - **ticker**: Stock ticker symbol (e.g., AAPL, MSFT)
    - **period**: Period label
    - **quarterly**: Whether to use quarterly data
    - **name**: Optional company name override
    """
    try:
        return services.ingest_yahoo(
            session,
            ticker=ticker,
            period_label=period,
            quarterly=quarterly,
            company_name=name
        )
    except Exception as e:
        logger.error(f"Error ingesting Yahoo Finance data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Analysis Routes
# ============================================================================

@app.get("/finance/analysis/{ticker}", tags=["Analysis"])
async def finance_analysis(ticker: str, quarterly: bool = Query(True)):
    """
    Enhanced financial analysis for a ticker symbol.
    
    - **ticker**: Stock ticker symbol
    - **quarterly**: Whether to analyze quarterly data
    """
    try:
        return analyze_ticker(ticker, quarterly=quarterly)
    except Exception as e:
        logger.error(f"Error in finance analysis for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
