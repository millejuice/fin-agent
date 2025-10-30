import React from 'react'
import { KPI } from "../types";

export default function KpiCards({ kpi }: { kpi: KPI | null }): React.ReactElement | null {
  if (!kpi) return null;
  const items: [string, number | undefined | null][] = [
    ["매출", kpi.revenue],
    ["영업이익", kpi.op_income],
    ["순이익", kpi.net_income],
    ["자산총계", kpi.total_assets],
    ["부채총계", kpi.total_liabilities],
    ["부채비율(%)", kpi.debt_ratio],
    ["영업CF", kpi.operating_cf],
    ["재고", kpi.inventory],
  ];
  return (
    <div className="grid cols-4">
      {items.map(([label, val]) => (
        <div key={label} className="card">
          <div className="kpi">
            <div className="kpi__label">{label}</div>
            <div className="kpi__value">{val ?? "-"}</div>
            <svg className="kpi__spark" viewBox="0 0 100 36" preserveAspectRatio="none">
              <polyline points="4,28 16,22 28,26 40,18 52,14 64,20 76,10 88,16 96,8" fill="none" stroke="rgba(79,140,255,0.9)" strokeWidth="2" />
            </svg>
          </div>
        </div>
      ))}
    </div>
  );
}
