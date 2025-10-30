import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Company, KPI, ValuationOutput } from "../types";
import ValuationForm from "../components/ValuationForm";
import ValuationResult from "../components/ValuationResult";

export default function ValuationPage(){
  const [companies, setCompanies] = useState<Company[]>([]);
  const [companyId, setCompanyId] = useState<number|undefined>();
  const [kpis, setKpis] = useState<KPI[]>([]);
  const [period, setPeriod] = useState<string>("");
  const [result, setResult] = useState<ValuationOutput|null>(null);

  useEffect(()=>{ api.companies().then((r:Company[])=>setCompanies(r)); }, []);
  useEffect(()=>{
    if(!companyId) return;
    api.kpis(companyId).then((rows:KPI[])=>{
      setKpis(rows);
      if(rows.length) setPeriod(rows[rows.length-1].period);
    })
  }, [companyId]);

  return (
    <div>
      <h2>Valuation</h2>
      <div style={{display:"flex", gap:12}}>
        <select value={companyId ?? ""} onChange={e=>setCompanyId(e.target.value? Number(e.target.value): undefined)}>
          <option value="">회사 선택</option>
          {companies.map(c=> <option key={c.id} value={String(c.id)}>{c.name}</option>)}
        </select>
        <select value={period} onChange={e=>setPeriod(e.target.value)}>
          <option value="">기간 선택</option>
          {kpis.map(k=> <option key={k.id} value={k.period}>{k.period}</option>)}
        </select>
      </div>

      {companyId && period && (
        <>
          <ValuationForm companyId={companyId} period={period} onResult={setResult}/>
          <ValuationResult v={result}/>
        </>
      )}
    </div>
  );
}
