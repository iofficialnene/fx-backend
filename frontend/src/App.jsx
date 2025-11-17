import React, { useEffect, useState } from "react";
import { fetchConfluence } from "./api";

const TFs = ["Weekly","Daily","H4","H1"];

function TrendBadge({text}) {
  const cls = text.includes("Strong Bullish") ? "badge strong-bullish"
            : text.includes("Bullish") ? "badge bullish"
            : text.includes("Strong Bearish") ? "badge strong-bearish"
            : text.includes("Bearish") ? "badge bearish"
            : "badge neutral";
  return <span className={cls}>{text || "—"}</span>;
}

function PairCard({item}) {
  const c = item.Confluence;
  const pct = item.ConfluencePercent || 0;
  return (
    <div className="card">
      <div className="card-header">
        <h2>{item.Pair}</h2>
        <div className="pct">{pct}%</div>
      </div>

      <div className="bars">
        {TFs.map(tf => (
          <div key={tf} className="bar-row">
            <div className="tf">{tf}</div>
            <div className="tf-value"><TrendBadge text={c[tf]} /></div>
          </div>
        ))}
      </div>
      <div className="meter">
        <div className="meter-fill" style={{width:`${pct}%`}}></div>
      </div>
    </div>
  );
}

export default function App(){
  const [data,setData] = useState([]);
  const [filter,setFilter] = useState("All");
  useEffect(() => {
    fetchConfluence().then(setData).catch(err => {
      console.error("fetch err", err);
      setData([]);
    });
  }, []);

  const filters = ["All","Strong Bullish","Strong Bearish","Bullish","Bearish","No Confluence"];

  const shown = data.filter(item => {
    if(filter === "All") return true;
    if(filter === "No Confluence") return item.ConfluencePercent === 0;
    // any timeframe matching
    return Object.values(item.Confluence).some(v => v && v.includes(filter));
  });

  return (
    <div className="app">
      <header className="topbar">
        <h1>FX Confluence Dashboard</h1>
        <div className="filters">
          {filters.map(f => (
            <button
              key={f}
              className={f === filter ? "active" : ""}
              onClick={() => setFilter(f)}
            >{f}</button>
          ))}
        </div>
      </header>

      <main className="grid">
        {shown.length === 0 && <div className="empty">No data yet — check backend or refresh</div>}
        {shown.map(item => <PairCard key={item.Symbol} item={item} />)}
      </main>
    </div>
  );
}
