"""
Database models for financial data.
"""
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy.types import JSON


class Company(SQLModel, table=True):
    """Company model representing a business entity."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(..., description="Company name")
    ticker: Optional[str] = Field(default="", description="Stock ticker symbol")
    sector: Optional[str] = Field(default=None, description="Business sector")
    industry: Optional[str] = Field(default=None, description="Industry classification")
    currency: Optional[str] = Field(default=None, description="Reporting currency")


class KPI(SQLModel, table=True):
    """
    Key Performance Indicator model for financial metrics.
    
    Stores financial data for a specific company and period.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id", description="Reference to company")
    period: str = Field(..., description="Period identifier (e.g., '2024-Q4')")
    freq: str = Field(default="quarterly", description="Frequency: 'quarterly' or 'annual'")

    # Income Statement
    revenue: Optional[float] = Field(default=None, description="Total revenue")
    gross_profit: Optional[float] = Field(default=None, description="Gross profit")
    op_income: Optional[float] = Field(default=None, description="Operating income (EBIT)")
    ebit: Optional[float] = Field(default=None, description="Earnings Before Interest and Taxes")
    ebitda: Optional[float] = Field(default=None, description="EBITDA")
    net_income: Optional[float] = Field(default=None, description="Net income")
    
    # Balance Sheet
    total_assets: Optional[float] = Field(default=None, description="Total assets")
    total_liabilities: Optional[float] = Field(default=None, description="Total liabilities")
    equity: Optional[float] = Field(default=None, description="Shareholders' equity")
    inventory: Optional[float] = Field(default=None, description="Inventory value")
    receivables: Optional[float] = Field(default=None, description="Accounts receivable")
    payables: Optional[float] = Field(default=None, description="Accounts payable")
    cash: Optional[float] = Field(default=None, description="Cash and cash equivalents")
    debt: Optional[float] = Field(default=None, description="Total debt")
    
    # Cash Flow
    operating_cf: Optional[float] = Field(default=None, description="Operating cash flow")
    invest_cf: Optional[float] = Field(default=None, description="Investing cash flow")
    finance_cf: Optional[float] = Field(default=None, description="Financing cash flow")
    capex: Optional[float] = Field(default=None, description="Capital expenditures")
    
    # Derived metrics
    debt_ratio: Optional[float] = Field(default=None, description="Debt ratio (liabilities/assets * 100)")
    
    # Metadata
    meta: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional metadata in JSON format"
    )
