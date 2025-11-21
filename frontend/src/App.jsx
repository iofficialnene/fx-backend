// src/App.jsx
import React, { useEffect, useState, useCallback } from "react";
import { fetchConfluence } from "./api";
import "./style.css"; // make sure this file exists (content provided below)

const TFs = ["Weekly", "Daily", "H4", "H1"];

function TrendBadge({ text }) {
  const txt = text || "";
  const cls =
    txt.includes("Strong Bullish") ? "badge strong-bullish" :
    txt.includes("Bullish") ? "badge bullish" :
    txt.includes("Strong Bearish") ? "badge strong-bearish" :
    txt.includes("Bearish") ? "badge bearish" :
    "badge neutral";

  return <span className={cls}>{txt || "—"}</span>;
}

function PairCard({ item }) {
  const c = item.Confluence || { Weekly: "", Daily: "", H4: "", H1: "" };
  const pct = Number(item.ConfluencePercent || 0);

  return (
    <article className="card">
      <div className="card-top">
        <div className="pair-title">
          <div className="pair-name">{item.Pair}</div>
          <div className="pair-symbol">{item.Symbol}</div>
        </div>
        <div className="pair-score">
          <div className="score-value">{pct}%</div>
          <div className="score-label">Confluence</div>
        </div>
      </div>

      <div className="bars">
        {TFs.map((tf) => (
          <div key={tf} className="bar-row">
            <div className="tf">{tf}</div>
            <div className="tf-value">
              <TrendBadge text={c[tf]} />
            </div>
          </div>
        ))}
      </div>

      <div className="meter">
        <div
          className="meter-fill"
          style={{ width: `${Math.max(0, Math.min(100, pct))}%` }}
          aria-hidden
        />
      </div>

      <div className="card-foot">
        <div className="summary">{item.Summary || (pct ? `${pct}%` : "No Confluence")}</div>
      </div>
    </article>
  );
}

export default function App() {
  const [data, setData] = useState([]);
  const [filter, setFilter] = useState("All");
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchConfluence();
      if (!res) {
        setError("No response from backend");
        setData([]);
      } else if (res.error) {
        setError(res.error);
        setData([]);
      } else {
        setData(res);
        setLastUpdated(new Date().toISOString());
      }
    } catch (e) {
      console.error("load error", e);
      setError(String(e));
      setData([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    // optional: you can set an interval to auto-refresh if desired:
    // const id = setInterval(load, 1000 * 60 * 2); // every 2 minutes
    // return () => clearInterval(id);
  }, [load]);

  const filters = ["All", "Strong Bullish", "Strong Bearish", "Bullish", "Bearish", "No Confluence"];

  const shown = data.filter((item) => {
    if (filter === "All") return true;
    if (filter === "No Confluence") return item.ConfluencePercent === 0;
    return Object.values(item.Confluence || {}).some(
      (v) => typeof v === "string" && v.includes(filter)
    );
  });

  return (
    <div className="app-root">
      <header className="topbar">
        <div className="brand">
          <h1>FX Confluence Dashboard</h1>
          <div className="meta">
            <button className="refresh-btn" onClick={load} disabled={loading}>
              {loading ? "Refreshing…" : "Refresh"}
            </button>
            {lastUpdated && <div className="updated">Updated: {new Date(lastUpdated).toLocaleString()}</div>}
          </div>
        </div>

        <nav className="filter-row">
          {filters.map((f) => (
            <button
              key={f}
              className={`filter-btn ${f === filter ? "active" : ""}`}
              onClick={() => setFilter(f)}
            >
              {f}
            </button>
          ))}
        </nav>
      </header>

      <main className="grid-wrap">
        {error && <div className="notice error">Error: {error}</div>}
        {!error && loading && <div className="notice">Loading data…</div>}
        {!error && !loading && shown.length === 0 && (
          <div className="notice">No data yet — refresh or check backend</div>
        )}

        <section className="grid">
          {shown.map((item) => (
            <PairCard key={item.Symbol || item.Pair} item={item} />
          ))}
        </section>
      </main>

      <footer className="foot">
        <div>Backend: <code>https://backend-qxff.onrender.com</code></div>
        <div>Made for you — Official Nene</div>
      </footer>
    </div>
  );
}