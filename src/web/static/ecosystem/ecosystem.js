/* ── palette ── */
const COLORS = {
  "CEX":           "#60a5fa",   // blue
  "Bridge":        "#34d399",   // green
  "x402 Agent":    "#a78bfa",   // purple
  "Regular Wallet":"#64748b",   // slate
};

const SEGMENT_ORDER = ["CEX", "Bridge", "x402 Agent", "Regular Wallet"];

const TOKEN_COLORS = ["#60a5fa", "#a78bfa", "#34d399", "#f472b6", "#fb923c"];

Chart.defaults.color = "#64748b";
Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";

/* ── helpers ── */
function fmtVolume(v) {
  if (v >= 1e9) return (v / 1e9).toFixed(2) + "B";
  if (v >= 1e6) return (v / 1e6).toFixed(2) + "M";
  if (v >= 1e3) return (v / 1e3).toFixed(1) + "K";
  return v.toFixed(0);
}

function fmtNum(n) {
  return n.toLocaleString();
}

function pct(part, total) {
  if (!total) return "0%";
  return (part / total * 100).toFixed(1) + "%";
}

/* ── chart instances (kept for destroy-on-redraw) ── */
let chartVolDonut = null;
let chartTxBar    = null;
let chartTokenBar = null;
let chartTimeline = null;

function destroyAll() {
  [chartVolDonut, chartTxBar, chartTokenBar, chartTimeline].forEach(c => c && c.destroy());
}

/* ── state ── */
let compatibility = {};

/* ── init ── */
async function loadMeta() {
  const [netRes, compRes] = await Promise.all([
    fetch("/meta/networks"),
    fetch("/meta/compatibility"),
  ]);
  const { networks } = await netRes.json();
  compatibility = await compRes.json();

  const netSel = document.getElementById("network");
  netSel.innerHTML = networks
    .map(n => `<option value="${n.toLowerCase()}">${n}</option>`)
    .join("");

  updateTokenOptions();
}

function updateTokenOptions() {
  const network = document.getElementById("network").value;
  const tokens  = compatibility[network] || [];
  const sel     = document.getElementById("token");
  sel.innerHTML = `<option value="">All assets</option>` +
    tokens.map(t => `<option value="${t}">${t}</option>`).join("");
}

document.getElementById("network").addEventListener("change", updateTokenOptions);

document.getElementById("refresh").addEventListener("click", runAnalysis);

/* ── main analysis ── */
async function runAnalysis() {
  const network = document.getElementById("network").value;
  const token   = document.getElementById("token").value;

  setStatus("Loading…");
  document.getElementById("charts-grid").style.display = "none";
  document.getElementById("empty-state").style.display = "none";
  document.getElementById("kpis").style.display = "none";

  const qs = new URLSearchParams({ network });
  if (token) qs.set("token", token);

  try {
    const [overviewRes, tokenRes, timelineRes, agentsRes] = await Promise.all([
      fetch(`/api/ecosystem/overview?${qs}`),
      fetch(`/api/ecosystem/token-breakdown?network=${network}`),
      fetch(`/api/ecosystem/x402-timeline?${qs}`),
      fetch(`/api/ecosystem/top-agents?network=${network}&limit=20`),
    ]);

    const overview  = await overviewRes.json();
    const tokenData = await tokenRes.json();
    const timeline  = await timelineRes.json();
    const agents    = await agentsRes.json();

    clearStatus();
    destroyAll();
    renderKPIs(overview);
    renderVolumeDonut(overview);
    renderTxCountBar(overview);
    renderTokenBar(tokenData);
    renderAgentsTable(agents, network);
    renderTimeline(timeline);

    document.getElementById("charts-grid").style.display = "grid";
    document.getElementById("kpis").style.display = "block";
  } catch (e) {
    setStatus("Error loading data. Is the server running?");
    document.getElementById("empty-state").style.display = "flex";
  }
}

/* ── KPIs ── */
function renderKPIs(data) {
  document.getElementById("kpi-volume").textContent = fmtVolume(data.total_volume);
  document.getElementById("kpi-txs").textContent    = fmtNum(data.total_txs);

  const x402 = data.segments.find(s => s.label === "x402 Agent");
  if (x402) {
    document.getElementById("kpi-x402-share").textContent = pct(x402.volume,   data.total_volume);
    document.getElementById("kpi-x402-txs").textContent   = pct(x402.tx_count, data.total_txs);
  } else {
    document.getElementById("kpi-x402-share").textContent = "0%";
    document.getElementById("kpi-x402-txs").textContent   = "0%";
  }
}

/* ── Volume donut ── */
function renderVolumeDonut(data) {
  const ordered = SEGMENT_ORDER.map(
    lbl => data.segments.find(s => s.label === lbl) || { label: lbl, volume: 0 }
  ).filter(s => s.volume > 0);

  const labels  = ordered.map(s => s.label);
  const volumes = ordered.map(s => s.volume);
  const colors  = labels.map(l => COLORS[l] || "#94a3b8");

  const ctx = document.getElementById("chart-volume-donut").getContext("2d");
  chartVolDonut = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{ data: volumes, backgroundColor: colors, borderColor: "rgba(15,23,42,0.8)", borderWidth: 2, hoverOffset: 8 }],
    },
    options: {
      cutout: "65%",
      plugins: {
        legend: { position: "bottom", labels: { boxWidth: 10, padding: 14, font: { size: 12 } } },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.label}: ${fmtVolume(ctx.raw)} (${pct(ctx.raw, data.total_volume)})`,
          },
        },
      },
      animation: { animateScale: true },
    },
  });

  // center label — largest segment
  const top = ordered.reduce((a, b) => a.volume > b.volume ? a : b, ordered[0]);
  if (top) {
    document.getElementById("donut-center").innerHTML =
      `<div class="dc-value">${pct(top.volume, data.total_volume)}</div>` +
      `<div class="dc-label">${top.label}</div>`;
  }
}

/* ── Tx count bar ── */
function renderTxCountBar(data) {
  const ordered = SEGMENT_ORDER.map(
    lbl => data.segments.find(s => s.label === lbl) || { label: lbl, tx_count: 0 }
  ).filter(s => s.tx_count > 0);

  const labels   = ordered.map(s => s.label);
  const txCounts = ordered.map(s => s.tx_count);
  const colors   = labels.map(l => COLORS[l] || "#94a3b8");

  const ctx = document.getElementById("chart-txcount-bar").getContext("2d");
  chartTxBar = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        data: txCounts,
        backgroundColor: colors.map(c => c + "cc"),
        borderColor: colors,
        borderWidth: 1,
        borderRadius: 6,
      }],
    },
    options: {
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: { label: ctx => ` ${fmtNum(ctx.raw)} txs (${pct(ctx.raw, data.total_txs)})` },
        },
      },
      scales: {
        x: { grid: { color: "rgba(148,163,184,0.06)" } },
        y: {
          grid: { color: "rgba(148,163,184,0.06)" },
          ticks: { callback: v => fmtNum(v) },
        },
      },
    },
  });
}

/* ── Token bar (x402 only) ── */
function renderTokenBar(rows) {
  const noData = document.getElementById("no-x402-tokens");
  const canvas = document.getElementById("chart-token-bar");

  if (!rows.length) {
    noData.style.display = "block";
    canvas.style.display = "none";
    return;
  }
  noData.style.display = "none";
  canvas.style.display = "block";

  const labels  = rows.map(r => r.token);
  const volumes = rows.map(r => r.volume);
  const colors  = rows.map((_, i) => TOKEN_COLORS[i % TOKEN_COLORS.length]);

  const ctx = canvas.getContext("2d");
  chartTokenBar = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Volume",
        data: volumes,
        backgroundColor: colors.map(c => c + "cc"),
        borderColor: colors,
        borderWidth: 1,
        borderRadius: 6,
      }],
    },
    options: {
      indexAxis: "y",
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ` ${fmtVolume(ctx.raw)}` } },
      },
      scales: {
        x: {
          grid: { color: "rgba(148,163,184,0.06)" },
          ticks: { callback: v => fmtVolume(v) },
        },
        y: { grid: { display: false } },
      },
    },
  });
}

/* ── Top agents table ── */
function renderAgentsTable(rows, network) {
  const tbody  = document.getElementById("agents-tbody");
  const noMsg  = document.getElementById("no-agents");
  const table  = document.getElementById("agents-table");

  tbody.innerHTML = "";

  if (!rows.length) {
    noMsg.style.display  = "block";
    table.style.display  = "none";
    return;
  }
  noMsg.style.display = "none";
  table.style.display = "table";

  rows.forEach((agent, i) => {
    const short = agent.address.slice(0, 8) + "…" + agent.address.slice(-6);
    const flowUrl = `/flow?address=${agent.address}&network=${network}`;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="rank">${i + 1}</td>
      <td><a class="addr-link" href="${flowUrl}" title="${agent.address}">${short}</a></td>
      <td>${agent.top_token ? `<span class="token-pill">${agent.top_token}</span>` : "—"}</td>
      <td>${fmtNum(agent.tx_count)}</td>
      <td class="vol-cell">${fmtVolume(agent.volume)}</td>
    `;
    tbody.appendChild(tr);
  });
}

/* ── Timeline ── */
function renderTimeline(rows) {
  const noData = document.getElementById("no-timeline");
  const canvas = document.getElementById("chart-timeline");

  if (!rows.length) {
    noData.style.display = "block";
    canvas.style.display = "none";
    return;
  }
  noData.style.display = "none";
  canvas.style.display = "block";

  const labels   = rows.map(r => r.period);
  const txCounts = rows.map(r => r.tx_count);
  const volumes  = rows.map(r => r.volume);

  const ctx = canvas.getContext("2d");
  chartTimeline = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Tx Count",
          data: txCounts,
          borderColor: "#a78bfa",
          backgroundColor: "rgba(167,139,250,0.08)",
          yAxisID: "y",
          tension: 0.3,
          pointRadius: 3,
          fill: true,
        },
        {
          label: "Volume",
          data: volumes,
          borderColor: "#60a5fa",
          backgroundColor: "rgba(96,165,250,0.05)",
          yAxisID: "y1",
          tension: 0.3,
          pointRadius: 3,
          borderDash: [4, 3],
          fill: false,
        },
      ],
    },
    options: {
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { labels: { boxWidth: 10, padding: 16, font: { size: 12 } } },
        tooltip: {
          callbacks: {
            label: ctx => ctx.dataset.yAxisID === "y1"
              ? ` Volume: ${fmtVolume(ctx.raw)}`
              : ` Txs: ${fmtNum(ctx.raw)}`,
          },
        },
      },
      scales: {
        x:  { grid: { color: "rgba(148,163,184,0.06)" } },
        y:  {
          position: "left",
          grid: { color: "rgba(148,163,184,0.06)" },
          ticks: { callback: v => fmtNum(v) },
          title: { display: true, text: "Tx Count", color: "#a78bfa" },
        },
        y1: {
          position: "right",
          grid: { drawOnChartArea: false },
          ticks: { callback: v => fmtVolume(v) },
          title: { display: true, text: "Volume", color: "#60a5fa" },
        },
      },
    },
  });
}

/* ── status helpers ── */
function setStatus(msg) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.style.display = "block";
}
function clearStatus() {
  const el = document.getElementById("status");
  el.style.display = "none";
}

/* ── boot ── */
loadMeta();
