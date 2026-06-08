let META = { networks: [], compatibility: {} };
let currentAddress = "";
let currentNetwork = "ethereum";
let currentToken = "";
let currentDir = "all";
let currentPage = 1;
let currentPageSize = 20;
let hasNextPage = false;
let visibleCount = 0;
let currentSortBy = "timestamp";
let currentSortOrder = "desc";
let currentCounterparty = "";
let currentPanelToken = "";

// USD prices per token unit — update XAUT when needed
const TOKEN_USD = {
  USDT: 1.00,
  USDC: 1.00,
  DAI:  1.00,
  XAUT: 3300.00,
};

const fmt = n => {
  const abs = Math.abs(n);
  const s = abs >= 1e9 ? (abs/1e9).toFixed(2)+"B"
           : abs >= 1e6 ? (abs/1e6).toFixed(2)+"M"
           : abs >= 1e3 ? (abs/1e3).toFixed(1)+"K"
           : abs.toFixed(2);
  return (n < 0 ? "-" : "") + s;
};

const shortAddr = a => a ? `${a.slice(0,6)}…${a.slice(-4)}` : "";

const fmtAmount = (value, token) => {
  const key = token?.toUpperCase();
  const price = TOKEN_USD[key];
  if (!price) return fmt(value);
  const usd = Math.abs(value * price);
  if (usd === 0) return "$0.00";
  if (usd < 0.01) return "<$0.01";
  const s = usd >= 1e9 ? (usd/1e9).toFixed(2)+"B"
           : usd >= 1e6 ? (usd/1e6).toFixed(2)+"M"
           : usd >= 1e3 ? (usd/1e3).toFixed(1)+"K"
           : usd.toFixed(2);
  return `$${s}`;
};

// ===== Load Meta =====

async function loadMeta() {
  const [nr, cr] = await Promise.all([
    fetch("/meta/networks"),
    fetch("/meta/compatibility"),
  ]);
  const { networks } = await nr.json();
  const compatibility = await cr.json();
  META.networks = networks || [];
  META.compatibility = compatibility;

  const sel = document.getElementById("network-select");
  sel.innerHTML = META.networks.map(n => `<option value="${n}">${n}</option>`).join("");
  sel.value = META.networks[0];

  updateTokenDropdown();
}

function updateTokenDropdown() {
  const networkSelect = document.getElementById("network-select");
  const tokenSelect = document.getElementById("token-select");
  const selectedNetwork = networkSelect.value;

  if (!selectedNetwork) {
    tokenSelect.innerHTML = '<option value="">Select a network first</option>';
    return;
  }

  const compatibleAssets = META.compatibility[selectedNetwork.toLowerCase()] || [];

  tokenSelect.innerHTML = `
    <option value="">All tokens</option>
    ${compatibleAssets.map(a => `<option value="${a}">${a}</option>`).join("")}
  `;
}

// ===== Search =====

async function search() {
  const address = document.getElementById("address-input").value.trim().toLowerCase();
  const network = document.getElementById("network-select").value;
  const token   = document.getElementById("token-select").value;

  const errEl = document.getElementById("error-msg");
  errEl.style.display = "none";

  if (!address || !address.startsWith("0x")) {
    errEl.textContent = "Enter a valid wallet address starting with 0x.";
    errEl.style.display = "block";
    return;
  }

  currentAddress      = address;
  currentNetwork      = network;
  currentToken        = token;
  currentDir          = "all";
  currentPage         = 1;
  currentCounterparty = "";
  currentPanelToken   = "";

  const btn = document.getElementById("search-btn");
  btn.textContent = "Loading…";
  btn.disabled = true;

  try {
    const params = new URLSearchParams({ address, network, ...(token && { token }) });
    currentSortBy = "timestamp";
    currentSortOrder = "desc";
    const [summary, transfers, counterparties] = await Promise.all([
      fetch(`/api/flow/summary?${params}`).then(r => r.json()),
      fetch(`/api/flow/transfers?${params}&direction=all&limit=${currentPageSize + 1}&offset=0&sort_by=timestamp&sort_order=desc`).then(r => r.json()),
      fetch(`/api/flow/counterparties?${params}&limit=10`).then(r => r.json()),
    ]);

    if (summary.error) {
      errEl.textContent = summary.error;
      errEl.style.display = "block";
      document.getElementById("results").style.display = "none";
      return;
    }

    renderSummary(summary);
    renderTransfers(transfers);
    renderCounterparties(counterparties);
    populateTokenChips();
    populateCounterpartyChips(counterparties);
    document.getElementById("results").style.display = "block";
  } catch(e) {
    errEl.textContent = "Failed to fetch data. Is the server running?";
    errEl.style.display = "block";
  } finally {
    btn.textContent = "Search";
    btn.disabled = false;
  }
}

// ===== Summary Cards =====

function renderSummary(s) {
  const netUsd = fmtAmount(Math.abs(s.net_flow), currentToken);
  const net = s.net_flow >= 0
    ? `<span style="color:#4ade80">+${netUsd}</span>`
    : `<span style="color:#f87171">-${netUsd}</span>`;

  let entityBadges = "";
  if (s.is_x402) entityBadges += `<span class="entity-badge">x402</span>`;
  (s.entity_class || []).forEach(c => { entityBadges += `<span class="entity-badge">${c}</span>`; });

  document.getElementById("summary-cards").innerHTML = `
    <div class="summary-card">
      <div class="label">Address</div>
      <div class="value" style="font-size:12px; font-family:monospace; word-break:break-all">${s.address}</div>
      <div class="sub">${entityBadges || "Regular wallet"}</div>
    </div>
    <div class="summary-card">
      <div class="label">Active Period</div>
      <div class="value" style="font-size:14px">${s.first_seen?.slice(0,10) ?? "—"}</div>
      <div class="sub">to ${s.last_seen?.slice(0,10) ?? "—"}</div>
    </div>
    <div class="summary-card">
      <div class="label">Transactions</div>
      <div class="value">${(s.sent_count + s.recv_count).toLocaleString()}</div>
      <div class="sub"><span style="color:#4ade80">${s.sent_count.toLocaleString()} sent</span> · <span style="color:#f87171">${s.recv_count.toLocaleString()} received</span></div>
    </div>
    <div class="summary-card">
      <div class="label">Total Sent</div>
      <div class="value" style="color:#f87171">${fmtAmount(s.sent_volume, currentToken)}</div>
      <div class="sub">outflow</div>
    </div>
    <div class="summary-card">
      <div class="label">Total Received</div>
      <div class="value" style="color:#4ade80">${fmtAmount(s.recv_volume, currentToken)}</div>
      <div class="sub">inflow</div>
    </div>
    <div class="summary-card">
      <div class="label">Net Flow</div>
      <div class="value" style="font-size:18px">${net}</div>
      <div class="sub">received − sent</div>
    </div>
  `;
}

// ===== Transfers Table =====

const SORT_COLS = [
  { key: "timestamp", label: "Time" },
  { key: "direction", label: "Direction" },
  { key: "counterparty", label: "Counterparty", nosort: true },
  { key: "token",     label: "Token" },
  { key: "value",     label: "Amount" },
];

function renderTransferHeaders() {
  const thead = document.querySelector("#transfers-table thead tr");
  if (!thead) return;
  thead.innerHTML = SORT_COLS.map(col => {
    if (col.nosort) return `<th>${col.label}</th>`;
    const active = currentSortBy === col.key;
    const arrow = active ? (currentSortOrder === "asc" ? " ↑" : " ↓") : "";
    return `<th class="sortable-th${active ? " sort-active" : ""}" data-sort="${col.key}">${col.label}${arrow}</th>`;
  }).join("");

  thead.querySelectorAll(".sortable-th").forEach(th => {
    th.addEventListener("click", () => {
      const key = th.dataset.sort;
      if (currentSortBy === key) {
        currentSortOrder = currentSortOrder === "desc" ? "asc" : "desc";
      } else {
        currentSortBy = key;
        currentSortOrder = "desc";
      }
      currentPage = 1;
      loadTransfersForDir(currentDir);
    });
  });
}

function renderTransfers(rows) {
  hasNextPage = rows.length > currentPageSize;
  const visible = rows.slice(0, currentPageSize);
  visibleCount = visible.length;

  renderTransferHeaders();

  const tbody = document.getElementById("transfers-body");
  if (!visible.length) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#475569; padding:24px">No transfers found</td></tr>`;
  } else {
    tbody.innerHTML = visible.map(r => {
      const counterparty = r.direction === "sent" ? r.to : r.from;
      return `
        <tr>
          <td style="color:#64748b; font-family:sans-serif">${r.timestamp ?? "—"}</td>
          <td><span class="dir-badge ${r.direction}">${r.direction === "sent" ? "OUT" : "IN"}</span></td>
          <td class="address-cell" title="${counterparty}" onclick="fillAddress('${counterparty}')">${shortAddr(counterparty)}</td>
          <td style="font-family:sans-serif; color:#94a3b8">${r.token}</td>
          <td style="text-align:right; color:${r.direction==='sent'?'#f87171':'#4ade80'}">${fmtAmount(r.value, r.token)}</td>
        </tr>`;
    }).join("");
  }

  renderPagination();
}

function renderPagination() {
  const el = document.getElementById("pagination-controls");
  if (!el) return;
  const start = (currentPage - 1) * currentPageSize + 1;
  const end = start + visibleCount - 1;
  el.innerHTML = `
    <div class="pagination-bar">
      <div class="pagination-left">
        <span class="pg-page-label">Page ${currentPage}</span>
        <span class="pg-sep">·</span>
        <span class="pg-range">${start}–${end}</span>
        <span class="pg-sep">·</span>
        <span class="pg-per-label">Rows per page</span>
        <select id="page-size-select" class="pg-size-select">
          <option value="20" ${currentPageSize===20?"selected":""}>20</option>
          <option value="50" ${currentPageSize===50?"selected":""}>50</option>
          <option value="100" ${currentPageSize===100?"selected":""}>100</option>
        </select>
      </div>
      <div class="pagination-right">
        <button class="pg-btn" id="pg-prev" ${currentPage === 1 ? "disabled" : ""}>‹</button>
        <button class="pg-btn" id="pg-next" ${!hasNextPage ? "disabled" : ""}>›</button>
      </div>
    </div>
  `;

  document.getElementById("pg-prev").addEventListener("click", () => {
    if (currentPage > 1) { currentPage--; loadTransfersForDir(currentDir); }
  });
  document.getElementById("pg-next").addEventListener("click", () => {
    if (hasNextPage) { currentPage++; loadTransfersForDir(currentDir); }
  });
  document.getElementById("page-size-select").addEventListener("change", e => {
    currentPageSize = parseInt(e.target.value);
    currentPage = 1;
    loadTransfersForDir(currentDir);
  });
}

// ===== Counterparties =====

function makeChip(label, value, activeValue, onClick) {
  const active = value === activeValue;
  return `<button class="filter-chip${active ? " active" : ""}" data-value="${value}" onclick="(${onClick.toString()})('${value}')">${label}</button>`;
}

function populateTokenChips() {
  const el = document.getElementById("token-filter-chips");
  if (!el) return;
  const tokens = META.compatibility[currentNetwork?.toLowerCase()] || [];
  el.innerHTML = [
    `<button class="filter-chip active" data-value="">All</button>`,
    ...tokens.map(t => `<button class="filter-chip" data-value="${t}">${t}</button>`),
  ].join("");
  el.querySelectorAll(".filter-chip").forEach(btn => {
    btn.addEventListener("click", () => {
      if (!currentAddress) return;
      el.querySelectorAll(".filter-chip").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentPanelToken = btn.dataset.value;
      currentPage = 1;
      loadTransfersForDir(currentDir);
    });
  });
}

function populateCounterpartyChips(rows) {
  const el = document.getElementById("counterparty-filter-chips");
  if (!el) return;
  el.innerHTML = [
    `<button class="filter-chip active" data-value="">All</button>`,
    ...rows.map(r => `<button class="filter-chip" data-value="${r.address}" title="${r.address}">${shortAddr(r.address)}</button>`),
  ].join("");
  el.querySelectorAll(".filter-chip").forEach(btn => {
    btn.addEventListener("click", () => {
      if (!currentAddress) return;
      el.querySelectorAll(".filter-chip").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentCounterparty = btn.dataset.value;
      currentPage = 1;
      loadTransfersForDir(currentDir);
    });
  });
}

function renderCounterparties(rows) {
  const el = document.getElementById("counterparties-list");
  if (!rows.length) {
    el.innerHTML = `<p style="padding:24px; color:#475569; font-size:13px; text-align:center">No counterparties found</p>`;
    return;
  }
  el.innerHTML = rows.map((r, i) => {
    const volumes = [];
    if (r.sent_volume > 0) volumes.push(`<span style="color:#f87171">↑ ${fmtAmount(r.sent_volume, currentToken)}</span>`);
    if (r.recv_volume > 0) volumes.push(`<span style="color:#4ade80">↓ ${fmtAmount(r.recv_volume, currentToken)}</span>`);
    const txMeta = [
      r.sent_txs > 0 ? `${r.sent_txs} sent` : "",
      r.recv_txs > 0 ? `${r.recv_txs} recv` : "",
    ].filter(Boolean).join(" · ");
    return `
    <div class="counterparty-item" onclick="fillAddress('${r.address}')">
      <span class="cp-rank">#${i+1}</span>
      <div class="cp-info">
        <div class="cp-addr" title="${r.address}">${shortAddr(r.address)}</div>
        <div class="cp-meta">${txMeta}</div>
      </div>
      <div class="cp-vols">${volumes.join(" ")}</div>
    </div>`;
  }).join("");
}

// ===== Fill Address (no auto-search) =====

function fillAddress(address) {
  document.getElementById("address-input").value = address;
  document.getElementById("address-input").focus();
}

// ===== Direction Tabs =====

async function loadTransfersForDir(dir) {
  const offset = (currentPage - 1) * currentPageSize;
  const effectiveToken = currentPanelToken || currentToken;
  const params = new URLSearchParams({
    address: currentAddress,
    network: currentNetwork,
    direction: dir,
    limit: currentPageSize + 1,
    offset,
    sort_by: currentSortBy,
    sort_order: currentSortOrder,
    ...(effectiveToken && { token: effectiveToken }),
    ...(currentCounterparty && { counterparty: currentCounterparty }),
  });
  const rows = await fetch(`/api/flow/transfers?${params}`).then(r => r.json());
  renderTransfers(rows);
}

// ===== Event Listeners =====

document.getElementById("search-btn").addEventListener("click", search);
document.getElementById("address-input").addEventListener("keydown", e => { if (e.key === "Enter") search(); });
document.getElementById("network-select").addEventListener("change", () => { updateTokenDropdown(); loadSamples(); });
document.getElementById("token-select").addEventListener("change", loadSamples);
document.getElementById("sample-btn").addEventListener("click", loadSamples);

document.querySelectorAll("[data-dir]").forEach(btn => {
  btn.addEventListener("click", () => {
    if (!currentAddress) return;
    document.querySelectorAll("[data-dir]").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentDir = btn.dataset.dir;
    currentPage = 1;
    loadTransfersForDir(currentDir);
  });
});

// ===== Sample Addresses =====

async function loadSamples() {
  const network = document.getElementById("network-select").value;
  const token   = document.getElementById("token-select").value;
  const btn = document.getElementById("sample-btn");
  btn.textContent = "…";
  btn.disabled = true;

  const params = new URLSearchParams({ network, count: 5, ...(token && { token }) });
  const samples = await fetch(`/api/flow/sample?${params}`).then(r => r.json()).catch(() => []);

  document.getElementById("sample-list").innerHTML = samples.map(s => `
    <button class="sample-chip" onclick="fillAddress('${s.address}')" title="${s.address}">
      ${s.address.slice(0,6)}…${s.address.slice(-4)}
      <span style="color:#60a5fa; margin-left:5px; font-size:10px">${s.tx_count.toLocaleString()} txs</span>
    </button>
  `).join("");

  btn.textContent = "↻ Generate";
  btn.disabled = false;
}

// Check if address was passed via URL query param
const urlAddress = new URLSearchParams(window.location.search).get("address");
if (urlAddress) {
  document.getElementById("address-input").value = urlAddress;
}

// Fire meta and samples in parallel — don't wait for meta to finish before sampling
loadMeta();
loadSamples();
