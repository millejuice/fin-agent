import type { ValuationOutput } from "../types";

export default function ValuationResult({ v }: { v: ValuationOutput | null }) {
  if (!v) return null;
  const fmt = (x: number) => x.toLocaleString(undefined, { maximumFractionDigits: 2 });

  return (
    <div style={{ marginTop: 16 }}>
      <h3>Valuation Results</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12 }}>
        <div className="card">DCF / sh: <b>{fmt(v.dcf_value_per_share)}</b></div>
        <div className="card">Multiples / sh: <b>{fmt(v.multiples_value_per_share)}</b></div>
        <div className="card">Blended / sh: <b>{fmt(v.blended_value_per_share)}</b></div>
      </div>
      <div className="card" style={{ marginTop: 12 }}>
        Piotroski F-Score: <b>{v.f_score}</b> / 9
      </div>
      <div className="card" style={{ marginTop: 12 }}>
        <b>Notes</b>
        <ul>{v.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
      </div>
    </div>
  );
}
