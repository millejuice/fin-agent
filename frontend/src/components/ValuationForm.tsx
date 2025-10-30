import { useState } from "react";
import { api } from "../lib/api";
import type { ValuationAssumption, ValuationOutput } from "../types";

export default function ValuationForm({
  companyId, period, onResult,
}: {
  companyId: number;
  period: string;
  onResult: (v: ValuationOutput) => void;
}) {
  const [form, setForm] = useState<ValuationAssumption>({
    company_id: companyId,
    period,
    base_op_margin: 0.15,
    tax_rate: 0.21,
    revenue_cagr_years_1_5: 0.08,
    revenue_cagr_years_6_10: 0.04,
    terminal_growth: 0.02,
    reinvestment_rate: 0.25,
    use_ocf_capex: true,
    rf: 0.04, erp: 0.05, beta: 1.0, pre_tax_cost_of_debt: 0.05, target_debt_ratio: 0.2,
    peer_pe: 20, peer_pfcf: 18, peer_ev_ebit: 14,
  } as ValuationAssumption);

  const set = (k: keyof ValuationAssumption, v: any) =>
    setForm(prev => ({ ...prev, [k]: v }));

  const run = async () => {
    const res = await api.valuationRun({ ...form, company_id: companyId, period });
    onResult(res);
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12 }}>
      {/* …필드들… */}
      <div style={{ gridColumn: "1 / -1" }}>
        <button onClick={run} className="btn primary">Run Valuation</button>
      </div>
    </div>
  );
}
