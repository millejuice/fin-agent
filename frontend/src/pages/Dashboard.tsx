// src/pages/Dashboard.tsx
import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import type { Company, KPI, Insight } from "../types";
import KpiCards from "../components/KpiCards";
import InsightsPanel from "../components/InsightsPanel";

export default function Dashboard() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [companyId, setCompanyId] = useState<number | undefined>();
  const [kpis, setKpis] = useState<KPI[]>([]);
  const [period, setPeriod] = useState<string>("");
  const [current, setCurrent] = useState<KPI | null>(null);
  const [insights, setInsights] = useState<Insight | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // --- Yahoo Finance 검색 상태 ---
  const [ticker, setTicker] = useState("");
  const [finance, setFinance] = useState<any>(null);
  const [financeErr, setFinanceErr] = useState<string | null>(null);

  // 회사 목록
  useEffect(() => {
    let on = true;
    (async () => {
      try {
        const list = (await api.companies()) as Company[];
        if (!on) return;
        setCompanies(list ?? []);
        if (list?.length && !companyId) setCompanyId(list[0].id);
      } catch (e: any) {
        if (!on) return;
        setErr(e?.message ?? "회사 목록 로드 실패");
      }
    })();
    return () => { on = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 회사 선택 시 KPI
  useEffect(() => {
    if (!companyId) return;
    let on = true;
    setLoading(true);
    setErr(null);
    (async () => {
      try {
        const rows = (await api.kpis(companyId)) as KPI[];
        if (!on) return;
        setKpis(rows ?? []);
        if (rows?.length) {
          const last = rows[rows.length - 1];
          setPeriod(last.period);
          setCurrent(last);
        } else {
          setPeriod("");
          setCurrent(null);
        }
        setInsights(null);
      } catch (e: any) {
        if (!on) return;
        setErr(e?.message ?? "KPI 로드 실패");
      } finally {
        if (on) setLoading(false);
      }
    })();
    return () => { on = false; };
  }, [companyId]);

  // 기간 선택된 KPI
  const selectedKpi = useMemo(() => {
    if (!period) return current;
    return kpis.find(k => k.period === period) ?? current;
  }, [kpis, period, current]);

  // 인사이트 생성
  const loadInsights = async () => {
    if (!companyId || !period) return;
    setLoading(true);
    setErr(null);
    try {
      const ins = (await api.insights(companyId, period)) as Insight;
      setInsights(ins);
    } catch (e: any) {
      setErr(e?.message ?? "인사이트 생성 실패");
    } finally {
      setLoading(false);
    }
  };

  // 티커 검색
  const searchFinance = async () => {
    if (!ticker.trim()) return;
    setFinanceErr(null);
    setLoading(true);
    try {
      const res = await api.finance(ticker.trim().toUpperCase());
      setFinance(res);
    } catch (e: any) {
      setFinance(null);
      setFinanceErr(e?.message ?? "Finance API 호출 실패");
    } finally {
      setLoading(false);
    }
  };

  // Enter 키로 검색
  const onTickerKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") searchFinance();
  };

  return (
    <div>
      <h2 style={{ marginBottom: 12 }}>Dashboard</h2>

      {/* -------- PDF 업로드 기반 컨트롤 -------- */}
      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <select
          value={companyId ?? ""}
          onChange={(e) => setCompanyId(e.target.value ? Number(e.target.value) : undefined)}
        >
          <option value="">회사 선택</option>
          {companies.map((c) => (
            <option key={c.id} value={String(c.id)}>
              {c.name}{c.ticker ? ` (${c.ticker})` : ""}
            </option>
          ))}
        </select>

        <select value={period} onChange={(e) => setPeriod(e.target.value)}>
          <option value="">기간 선택</option>
          {kpis.map((k) => (
            <option key={k.id} value={k.period}>{k.period}</option>
          ))}
        </select>

        <button className="btn primary" onClick={loadInsights} disabled={!companyId || !period || loading}>
          인사이트 생성
        </button>

        {loading && <span style={{ opacity: 0.7 }}>로딩 중…</span>}
        {err && <span style={{ color: "#ff6b6b" }}>⚠ {err}</span>}
      </div>

      {/* KPI 카드 */}
      <div style={{ marginTop: 16 }}>
        <KpiCards kpi={selectedKpi ?? null} />
      </div>

      {/* 인사이트 */}
      <div style={{ marginTop: 16 }}>
        <InsightsPanel data={insights} />
      </div>

      {/* -------- Yahoo Finance 검색 섹션 -------- */}
      <hr style={{ margin: "28px 0" }} />
      <h3 style={{ marginBottom: 8 }}>티커/회사 검색 (Yahoo Finance)</h3>

      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <input
          type="text"
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          onKeyDown={onTickerKeyDown}
          placeholder="예: AAPL, MSFT, TSLA"
          style={{ minWidth: 220, padding: "8px 10px", borderRadius: 8 }}
        />
        <button className="btn" onClick={searchFinance} disabled={loading}>검색</button>
        {financeErr && <span style={{ color: "#ff6b6b" }}>⚠ {financeErr}</span>}
      </div>

      {finance && (
        <div style={{ marginTop: 16, display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
          <div className="card">
            <div className="card-title">요약</div>
            <div className="card-body">
              <div style={{ fontWeight: 700, fontSize: 18 }}>
                {finance.summary?.name} ({finance.summary?.ticker})
              </div>
              <div>섹터: {finance.summary?.sector ?? "-"}</div>
              <div>산업: {finance.summary?.industry ?? "-"}</div>
              <div>시가총액: {finance.summary?.marketCap?.toLocaleString?.() ?? finance.summary?.marketCap ?? "-"}</div>
            </div>
          </div>

          <div className="card">
            <div className="card-title">밸류에이션</div>
            <div className="card-body">
              <div>PER: {finance.summary?.peRatio ?? "-"}</div>
              <div>PBR: {finance.summary?.pbRatio ?? "-"}</div>
              <div>EPS: {finance.summary?.eps ?? "-"}</div>
              <div>배당수익률: {finance.summary?.dividendYield ?? "-"}</div>
            </div>
          </div>

          <div className="card" style={{ gridColumn: "1 / -1" }}>
            <div className="card-title">인사이트</div>
            <div className="card-body">
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {(finance.insights ?? []).map((s: string, i: number) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
