let META = { networks: [], compatibility: {} };
let currentAddress = "";
let currentNetwork = "ethereum";
let currentToken = "";
let currentDir = "all";

const fmt = n => {
  const abs = Math.abs(n);
  const s = abs >= 1e9 ? (abs/1e9).toFixed(2)+"B"
           : abs >= 1e6 ? (abs/1e6).toFixed(2)+"M"
           : abs >= 1e3 ? (abs/1e3).toFixed(1)+"K"
           : abs.toFixed(2);
  return (n < 0 ? "-" : "") + s;
};

const shortAddr = a => a ? `${a.slice(0,6)}…${a.slice(-4)}` : "";

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

  currentAddress = address;
  currentNetwork = network;
  currentToken   = token;
  currentDir     = "all";
  document.querySelectorAll(".dir-tab").forEach(t => t.classList.toggle("active", t.dataset.dir === "all"));

  const btn = document.getElementById("search-btn");
  btn.textContent = "Loading…";
  btn.disabled = true;

  try {
    const params = new URLSearchParams({ address, network, ...(token && { token }) });
    const [summary, transfers, counterparties] = await Promise.all([
      fetch(`/api/flow/summary?${params}`).then(r => r.json()),
      fetch(`/api/flow/transfers?${params}&direction=all&limit=50`).then(r => r.json()),
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
  const net = s.net_flow >= 0
    ? `<span style="color:#4ade80">+${fmt(s.net_flow)}</span>`
    : `<span style="color:#f87171">${fmt(s.net_flow)}</span>`;

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
      <div class="sub">${s.sent_count.toLocaleString()} sent · ${s.recv_count.toLocaleString()} received</div>
    </div>
    <div class="summary-card">
      <div class="label">Total Sent</div>
      <div class="value" style="color:#f87171">${fmt(s.sent_volume)}</div>
      <div class="sub">outflow</div>
    </div>
    <div class="summary-card">
      <div class="label">Total Received</div>
      <div class="value" style="color:#4ade80">${fmt(s.recv_volume)}</div>
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

function renderTransfers(rows) {
  const tbody = document.getElementById("transfers-body");
  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#475569; padding:24px">No transfers found</td></tr>`;
    return;
  }
  tbody.innerHTML = rows.map(r => {
    const counterparty = r.direction === "sent" ? r.to : r.from;
    return `
      <tr>
        <td style="color:#64748b; font-family:sans-serif">${r.timestamp ?? "—"}</td>
        <td><span class="dir-badge ${r.direction}">${r.direction === "sent" ? "OUT" : "IN"}</span></td>
        <td class="address-cell" title="${counterparty}" onclick="drillDown('${counterparty}')">${shortAddr(counterparty)}</td>
        <td style="font-family:sans-serif; color:#94a3b8">${r.token}</td>
        <td style="text-align:right; color:${r.direction==='sent'?'#f87171':'#4ade80'}">${fmt(r.value)}</td>
      </tr>`;
  }).join("");
}

// ===== Counterparties =====

function renderCounterparties(rows) {
  const el = document.getElementById("counterparties-list");
  if (!rows.length) {
    el.innerHTML = `<p style="padding:24px; color:#475569; font-size:13px; text-align:center">No counterparties found</p>`;
    return;
  }
  el.innerHTML = rows.map((r, i) => `
    <div class="counterparty-item" onclick="drillDown('${r.address}')">
      <span class="cp-rank">#${i+1}</span>
      <div class="cp-info">
        <div class="cp-addr" title="${r.address}">${r.address}</div>
        <div class="cp-meta">${r.total_txs.toLocaleString()} txs · ${r.relation}</div>
      </div>
      <div class="cp-vol">${fmt(r.total_volume)}</div>
    </div>
  `).join("");
}

// ===== Drill Down =====

function drillDown(address) {
  document.getElementById("address-input").value = address;
  search();
}

// ===== Direction Tabs =====

async function loadTransfersForDir(dir) {
  const params = new URLSearchParams({
    address: currentAddress,
    network: currentNetwork,
    direction: dir,
    limit: 50,
    ...(currentToken && { token: currentToken }),
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

document.querySelectorAll(".dir-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    if (!currentAddress) return;
    document.querySelectorAll(".dir-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    currentDir = tab.dataset.dir;
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
    <button class="sample-chip" onclick="drillDown('${s.address}')" title="${s.address}">
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
