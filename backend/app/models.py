# app/models.py
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy.types import JSON  # ⬅️ 추가

class Company(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    ticker: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    currency: Optional[str] = None

class KPI(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id")
    period: str
    freq: str

    revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    ebit: Optional[float] = None
    ebitda: Optional[float] = None
    net_income: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    equity: Optional[float] = None
    oper_cf: Optional[float] = None
    invest_cf: Optional[float] = None
    finance_cf: Optional[float] = None
    capex: Optional[float] = None
    inventory: Optional[float] = None
    receivables: Optional[float] = None
    payables: Optional[float] = None
    cash: Optional[float] = None
    debt: Optional[float] = None

    # ❗️여기를 JSON 컬럼으로
    meta: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON)
    )
