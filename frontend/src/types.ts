export interface Company {
  id: number;
  name: string;
  ticker?: string;   // 선택적 속성으로 추가
}

export type KPI = {
  id: number; company_id: number; period: string;
  revenue?: number; op_income?: number; net_income?: number;
  total_assets?: number; total_liabilities?: number;
  operating_cf?: number; inventory?: number; debt_ratio?: number;
  capex?: number; shares_outstanding?: number; cash_and_equiv?: number; total_debt?: number;
};
export type Insight = { summary: string[]; risks: string[]; watchlist: string[]; rules_fired: string[]; };

export type ValuationAssumption = {
  company_id: number; period: string;
  base_revenue?: number; base_op_margin: number; tax_rate: number;
  revenue_cagr_years_1_5: number; revenue_cagr_years_6_10: number; terminal_growth: number;
  reinvestment_rate: number; use_ocf_capex: boolean; capex_override?: number|null; ocf_override?: number|null;
  rf: number; erp: number; beta: number; pre_tax_cost_of_debt: number; target_debt_ratio: number;
  peer_pe?: number|null; peer_pfcf?: number|null; peer_ev_ebit?: number|null;
  shares_outstanding?: number|null; cash_and_equiv?: number|null; total_debt?: number|null;
};
export type SensitivityCell = { x:number; y:number; value_per_share:number; };
export type ValuationOutput = {
  dcf_value_per_share: number;
  multiples_value_per_share: number;
  blended_value_per_share: number;
  f_score: number;
  notes: string[];
  sensitivity: SensitivityCell[];
};
export type FinanceAnalysis = {
  meta: { ticker:string; name:string; sector?:string; industry?:string; marketCap?:number; currency:string; asOf:string; };
  multiples: { pe?:number|null; pbr?:number|null; eps?:number|null; dividendYield?:number|null; };
  trend: Record<string, Record<string, number>>;
  benchmarks: Record<string, number|null>;
  flags: {type:"warning"|"watch"; msg:string;}[];
  confidence: number;
};


