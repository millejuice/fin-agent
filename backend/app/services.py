"""
Business logic services for financial data operations.
"""
import os
from typing import Dict, List, Optional
from sqlmodel import Session, select
from fastapi import UploadFile, HTTPException

from app.models import Company, KPI
from app.parser import parse_pdf_to_kpi
from app.yahoo import fetch_yahoo_financials
from app.config import settings
from app.logger import get_logger

logger = get_logger("services")


def save_pdf(file: UploadFile) -> str:
    """
    Save uploaded PDF file to disk.
    
    Args:
        file: FastAPI UploadFile object
        
    Returns:
        Path to saved file
        
    Raises:
        HTTPException: If file save fails
    """
    try:
        upload_dir = settings.get_upload_dir()
        filename = file.filename or "unknown.pdf"
        path = os.path.join(upload_dir, filename)
        
        with open(path, "wb") as f:
            content = file.file.read()
            if len(content) > settings.MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE} bytes"
                )
            f.write(content)
        
        logger.info(f"Saved PDF file: {filename} ({len(content)} bytes)")
        return path
    except Exception as e:
        logger.error(f"Failed to save PDF file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")


def upsert_company(
    session: Session, 
    name: str, 
    ticker: Optional[str] = None
) -> Company:
    """
    Create or update a company record.
    
    Args:
        session: Database session
        name: Company name
        ticker: Optional stock ticker symbol
        
    Returns:
        Company model instance
    """
    try:
        # Try to find existing company by name
        company = session.exec(
            select(Company).where(Company.name == name)
        ).first()
        
        if company:
            # Update ticker if provided and different
            if ticker and company.ticker != ticker:
                company.ticker = ticker
                session.add(company)
                session.commit()
                session.refresh(company)
                logger.info(f"Updated company {name} with ticker {ticker}")
            return company
        
        # Create new company
        company = Company(name=name, ticker=ticker or "")
        session.add(company)
        session.commit()
        session.refresh(company)
        logger.info(f"Created new company: {name} (ticker: {ticker})")
        return company
        
    except Exception as e:
        logger.error(f"Error upserting company {name}: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def upsert_kpi(
    session: Session, 
    company_id: int, 
    period: str, 
    data: Dict[str, float],
    freq: str = "quarterly"
) -> KPI:
    """
    Create or update a KPI record.
    
    Args:
        session: Database session
        company_id: Company ID
        period: Period identifier (e.g., "2024-Q4")
        data: Dictionary of KPI values
        freq: Frequency (quarterly/annual)
        
    Returns:
        KPI model instance
    """
    try:
        # Find existing KPI or create new
        kpi = session.exec(
            select(KPI).where(
                (KPI.company_id == company_id) & 
                (KPI.period == period)
            )
        ).first()
        
        if not kpi:
            kpi = KPI(company_id=company_id, period=period, freq=freq)
        
        # Update KPI fields from data
        for key, value in data.items():
            if hasattr(kpi, key) and value is not None:
                try:
                    setattr(kpi, key, float(value))
                except (ValueError, TypeError):
                    logger.warning(f"Could not set {key}={value}, skipping")
        
        # Calculate debt ratio if assets and liabilities are available
        if (kpi.total_assets and kpi.total_assets > 0 and 
            kpi.total_liabilities is not None):
            kpi.debt_ratio = (kpi.total_liabilities / kpi.total_assets) * 100.0
        
        session.add(kpi)
        session.commit()
        session.refresh(kpi)
        logger.info(f"Upserted KPI for company {company_id}, period {period}")
        return kpi
        
    except Exception as e:
        logger.error(f"Error upserting KPI: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def list_companies(session: Session) -> List[Company]:
    """
    List all companies.
    
    Args:
        session: Database session
        
    Returns:
        List of Company instances
    """
    try:
        return list(session.exec(select(Company).order_by(Company.name)).all())
    except Exception as e:
        logger.error(f"Error listing companies: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def list_kpis_by_company(session: Session, company_id: int) -> List[KPI]:
    """
    List all KPIs for a specific company, ordered by period.
    
    Args:
        session: Database session
        company_id: Company ID
        
    Returns:
        List of KPI instances
    """
    try:
        return list(
            session.exec(
                select(KPI)
                .where(KPI.company_id == company_id)
                .order_by(KPI.period)
            ).all()
        )
    except Exception as e:
        logger.error(f"Error listing KPIs for company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def handle_upload(
    session: Session, 
    file: UploadFile, 
    company: str, 
    period: str
) -> Dict[str, any]:
    """
    Handle PDF upload: parse, extract KPIs, and save to database.
    
    Args:
        session: Database session
        file: Uploaded PDF file
        company: Company name
        period: Period identifier
        
    Returns:
        Dictionary with upload result
    """
    try:
        # Save file
        path = save_pdf(file)
        
        # Parse PDF
        logger.info(f"Parsing PDF: {file.filename}")
        extracted = parse_pdf_to_kpi(path)
        
        if not extracted:
            raise HTTPException(
                status_code=400, 
                detail="No KPIs could be extracted from the PDF"
            )
        
        # Upsert company and KPI
        company_obj = upsert_company(session, company)
        upsert_kpi(session, company_obj.id, period, extracted)
        
        logger.info(
            f"Successfully processed upload: {company} - {period} "
            f"({len(extracted)} KPIs extracted)"
        )
        
        return {
            "company": company,
            "period": period,
            "extracted": extracted
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling upload: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Upload processing failed: {str(e)}"
        )


def ingest_yahoo(
    session: Session,
    ticker: str,
    period_label: str,
    *,
    quarterly: bool = False,
    company_name: Optional[str] = None
) -> Dict[str, any]:
    """
    Ingest financial data from Yahoo Finance for a ticker.
    
    Args:
        session: Database session
        ticker: Stock ticker symbol
        period_label: Period label (e.g., "2024-Q4")
        quarterly: Whether to use quarterly data
        company_name: Optional company name override
        
    Returns:
        Dictionary with ingestion result
    """
    try:
        # Upsert company
        name = company_name or ticker.upper()
        company = upsert_company(session, name=name, ticker=ticker.upper())
        
        # Fetch data from Yahoo Finance
        logger.info(f"Fetching Yahoo Finance data for {ticker}")
        data = fetch_yahoo_financials(ticker, use_quarterly=quarterly)
        
        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for ticker {ticker}"
            )
        
        # Map Yahoo Finance keys to KPI model fields
        kpi_data = {}
        field_mapping = {
            "revenue": "revenue",
            "operating_income": "op_income",
            "net_income": "net_income",
            "total_assets": "total_assets",
            "total_liabilities": "total_liabilities",
            "inventory": "inventory",
            "operating_cf": "operating_cf",
            "capex": "capex",
            "shares_outstanding": "shares_outstanding",
            "cash_and_equiv": "cash",
            "total_debt": "debt",
        }
        
        for yahoo_key, kpi_key in field_mapping.items():
            if yahoo_key in data and data[yahoo_key] is not None:
                kpi_data[kpi_key] = data[yahoo_key]
        
        # Upsert KPI
        freq = "quarterly" if quarterly else "annual"
        kpi = upsert_kpi(
            session, 
            company.id, 
            period_label, 
            kpi_data,
            freq=freq
        )
        
        logger.info(
            f"Successfully ingested Yahoo Finance data: {ticker} - {period_label}"
        )
        
        return {
            "company_id": company.id,
            "kpi_id": kpi.id,
            "period": kpi.period
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting Yahoo Finance data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Yahoo Finance ingestion failed: {str(e)}"
        )
