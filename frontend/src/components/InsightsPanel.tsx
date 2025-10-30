import React from 'react'
import { Insight } from "../types";

export default function InsightsPanel({ data }: { data: Insight | null }): React.ReactElement | null {
  if (!data) return null;
  return (
    <div className="grid cols-3">
      <div className="card headered">
        <div className="card__header">
          <div>요약</div>
        </div>
        <div className="card__body">
          <ul className="list">{data.summary.map((s,i)=><li key={i}>{s}</li>)}</ul>
        </div>
      </div>
      <div className="card headered">
        <div className="card__header">
          <div>리스크</div>
        </div>
        <div className="card__body">
          <ul className="list">{data.risks.map((s,i)=><li key={i} style={{color:"#ef4444"}}>{s}</li>)}</ul>
        </div>
      </div>
      <div className="card headered">
        <div className="card__header">
          <div>Watchlist</div>
        </div>
        <div className="card__body">
          <ul className="list">{data.watchlist.map((s,i)=><li key={i}>{s}</li>)}</ul>
        </div>
      </div>
    </div>
  );
}
