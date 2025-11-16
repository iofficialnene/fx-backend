// static/app.js
const API = "/confluence";
const grid = document.getElementById("cardsGrid");
const lastUpdatedEl = document.getElementById("lastUpdated");
const filterSelect = document.getElementById("filterSelect");
const refreshBtn = document.getElementById("refreshBtn");
const autoRefresh = document.getElementById("autoRefresh");
let autoTimer = null;

async function fetchData() {
  try {
    const res = await fetch(API);
    const json = await res.json();
    if (json.error) {
      grid.innerHTML = `<div class="card"><div class="pair">Error: ${json.error}</div><div>${json.details || ""}</div></div>`;
      return [];
    }
    return json;
  } catch (e) {
    grid.innerHTML = `<div class="card"><div class="pair">Network error</div><div>${e.message}</div></div>`;
    return [];
  }
}

function getTrendClass(str){
  if(!str) return "";
  if(str.includes("Strong Bullish")) return "Strong-Bullish";
  if(str.includes("Bullish")) return "Bullish";
  if(str.includes("Strong Bearish")) return "Strong-Bearish";
  if(str.includes("Bearish")) return "Bearish";
  return "";
}

function renderCard(item){
  const summaryClass = getTrendClass(item.Summary);
  const percent = item.ConfluencePercent || 0;
  // create card
  const div = document.createElement("div");
  div.className = "card styleA"; // change styleA..D as you prefer (or add UI to pick)
  div.innerHTML = `
    <div class="head row">
      <div class="pair">${item.Pair}</div>
      <div class="summary ${summaryClass.replace(" ", "-")}">${item.Summary}</div>
    </div>
    <div class="chips row">
      <div class="chip">Weekly: ${item.Confluence.Weekly || "—"}</div>
      <div class="chip">Daily: ${item.Confluence.Daily || "—"}</div>
      <div class="chip">H4: ${item.Confluence.H4 || "—"}</div>
      <div class="chip">H1: ${item.Confluence.H1 || "—"}</div>
    </div>
    <div>
      <div style="display:flex;justify-content:space-between;font-size:13px;margin-top:8px">
        <div>Confluence Strength</div>
        <div style="font-weight:700">${percent}%</div>
      </div>
      <div class="trend-bar" style="margin-top:6px">
        <div class="trend-fill ${percent>=50 ? 'green':'red'}" style="width:${percent}%"></div>
      </div>
    </div>
  `;
  return div;
}

function applyFilter(items){
  const f = filterSelect.value;
  if(f === "all") return items;
  return items.filter(i => i.Summary === f);
}

async function loadAndRender(){
  const data = await fetchData();
  const filtered = applyFilter(data);
  grid.innerHTML = "";
  if(!filtered.length){
    grid.innerHTML = `<div class="card"><div class="pair">No data</div><div class="chip">Try refreshing</div></div>`;
  } else {
    filtered.forEach(item => {
      grid.appendChild(renderCard(item));
    });
  }
  lastUpdatedEl.textContent = new Date().toLocaleString();
}

filterSelect.addEventListener("change", loadAndRender);
refreshBtn.addEventListener("click", loadAndRender);
autoRefresh.addEventListener("change", () => {
  if(autoTimer) { clearInterval(autoTimer); autoTimer = null; }
  const val = parseInt(autoRefresh.value, 10);
  if(val > 0) {
    autoTimer = setInterval(loadAndRender, val*1000);
  }
});

window.addEventListener("load", () => {
  loadAndRender();
  // default auto refresh off
});
