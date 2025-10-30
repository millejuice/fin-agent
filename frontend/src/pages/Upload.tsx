import { useState } from "react";
import { api } from "../lib/api";

export default function Upload() {
  const [file, setFile] = useState<File|null>(null);
  const [company, setCompany] = useState("SampleCorp");
  const [period, setPeriod] = useState("2024-Q4");
  const [msg, setMsg] = useState("");

  const onUpload = async () => {
    if (!file) return;
    setMsg("업로드/파싱 중...");
    const res = await api.upload(file, company, period);
    setMsg(`완료: ${res.company} ${res.period}`);
  };

  return (
    <div className="card headered form-card">
      <div className="card__header">
        <div>PDF 업로드</div>
        <div className="muted">재무 보고서에서 KPI와 인사이트를 추출합니다</div>
      </div>
      <div className="card__body">
        <div className="form-row">
          <input className="input" type="file" accept="application/pdf" onChange={e=>setFile(e.target.files?.[0]||null)} />
          <input className="input" value={company} onChange={e=>setCompany(e.target.value)} placeholder="회사명" />
          <input className="input" value={period} onChange={e=>setPeriod(e.target.value)} placeholder="YYYY-Qx" />
          <button className="btn primary" onClick={onUpload}>추출하기</button>
        </div>
        <div className="muted" style={{marginTop:8}}>{msg}</div>
      </div>
    </div>
  );
}
