// src/lib/api.ts
import axios from "axios";
import type { Company, KPI, Insight, ValuationAssumption, ValuationOutput } from "../types";

const BASE = "http://localhost:8000";

export const api = {
  upload: async (file: File, company: string, period: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("company", company);
    form.append("period", period);
    const { data } = await axios.post<{ company:string; period:string; extracted:Record<string,any> }>(`${BASE}/upload`, form);
    return data;
  },
  companies: async (): Promise<Company[]> => (await axios.get<Company[]>(`${BASE}/companies`)).data,
  kpis: async (companyId: number): Promise<KPI[]> => (await axios.get<KPI[]>(`${BASE}/kpis/${companyId}`)).data,
  insights: async (companyId: number, period: string): Promise<Insight> =>
    (await axios.get<Insight>(`${BASE}/insights/${companyId}/${period}`)).data,

  valuationRun: async (asm: ValuationAssumption): Promise<ValuationOutput> =>
    (await axios.post<ValuationOutput>(`${BASE}/valuation/run`, asm)).data,
  ingestYahoo: async (ticker: string, period: string, quarterly=false, name?: string) => {
    const params = new URLSearchParams({ ticker, period, quarterly: String(quarterly) });
    if (name) params.set("name", name);
    const r = await fetch(`http://localhost:8000/ingest/yahoo?${params.toString()}`, { method: "POST" });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  finance: async (ticker: string) => {
  const res = await axios.get(`${BASE}/finance/${ticker}`);
  return res.data;
},
analysis: async (ticker: string) =>
  (await axios.get(`${BASE}/finance/analysis/${ticker}`)).data,


};
