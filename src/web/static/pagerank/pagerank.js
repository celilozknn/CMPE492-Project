// ===== Graph Initialization =====

const svg = d3.select("#graph");
let simulation;
let currentGraph = null;

// ===== State Management =====

let META = {
  networks: [],
  stablecoins: [],
  compatibility: {}
};

// ===== Load Metadata =====

async function loadMeta() {
  try {
    const [networksRes, stablecoinsRes, compatibilityRes] = await Promise.all([
      fetch("/meta/networks"),
      fetch("/meta/stablecoins"),
      fetch("/meta/compatibility")
    ]);

    if (!networksRes.ok || !stablecoinsRes.ok || !compatibilityRes.ok) {
      throw new Error("Failed to load metadata");
    }

    const networks = await networksRes.json();
    const stablecoins = await stablecoinsRes.json();
    const compatibility = await compatibilityRes.json();

    META.networks = networks.networks || [];
    META.stablecoins = stablecoins.stablecoins || [];
    META.compatibility = compatibility;

    populateNetworkDropdown();
    updateAssetDropdown();
  } catch (error) {
    console.error("Error loading metadata:", error);
    document.getElementById("network").innerHTML = '<option value="">Failed to load</option>';
    document.getElementById("token").innerHTML = '<option value="">Failed to load</option>';
    showError("Failed to load network configuration. Is the server running?");
  }
}

// ===== Populate Network Dropdown =====

function populateNetworkDropdown() {
  const networkSelect = document.getElementById("network");
  
  if (META.networks.length === 0) {
    networkSelect.innerHTML = '<option value="">No networks available</option>';
    return;
  }

  networkSelect.innerHTML = META.networks
    .map(network => `<option value="${network}">${network}</option>`)
    .join("");

  // Set first network as default
  networkSelect.value = META.networks[0];
}

// ===== Update Asset Dropdown Based on Network =====

function updateAssetDropdown() {
  const networkSelect = document.getElementById("network");
  const tokenSelect = document.getElementById("token");
  const selectedNetwork = networkSelect.value;

  if (!selectedNetwork) {
    tokenSelect.innerHTML = '<option value="">Select a network first</option>';
    return;
  }

  // Get compatible stablecoins for selected network
  const compatibleAssets = META.compatibility[selectedNetwork.toLowerCase()] || [];

  tokenSelect.innerHTML = `
    <option value="">All assets</option>
    ${compatibleAssets
      .map(asset => `<option value="${asset}">${asset}</option>`)
      .join("")}
  `;
}

// ===== Load and Render Graph =====

async function loadGraph() {
  const btn = document.getElementById("refresh");
  const status = document.getElementById("graph-status");

  try {
    const network = document.getElementById("network").value;
    const token = document.getElementById("token").value || "";
    const topN = document.getElementById("topN").value;

    if (!network) {
      showError("Please select a network");
      return;
    }

    btn.disabled = true;
    btn.textContent = "Fetching…";
    status.textContent = "Fetching graph data…";
    status.style.color = "#94a3b8";

    const panel = document.getElementById("stats-panel");
    if (panel) panel.innerHTML = `<div style="font-size:12px;color:#475569">Loading dataset info…</div>`;

    const params = new URLSearchParams({ network, top_n: topN });
    if (token) params.append("token", token);

    const response = await fetch(`/api/graph?${params.toString()}`);
    if (!response.ok) throw new Error(`API error: ${response.status}`);

    const data = await response.json();

    if (data.error) { showError(data.error); return; }

    if (!data.nodes || data.nodes.length === 0) {
      status.textContent = "No data for selected filters.";
      status.style.color = "#f87171";
      return;
    }

    status.textContent = `Rendering ${data.nodes.length} nodes…`;
    currentGraph = data;
    renderGraph(data);
    status.textContent = `${data.nodes.length} nodes · ${data.edges.length} edges`;
    status.style.color = "#4ade80";

    const statsParams = new URLSearchParams({ network });
    if (token) statsParams.append("token", token);
    fetch(`/api/stats?${statsParams.toString()}`)
      .then(r => r.json())
      .then(renderStats)
      .catch(e => console.error("Stats fetch failed:", e));
  } catch (error) {
    console.error("Error loading graph:", error);
    showError("Failed to load graph data.");
    if (status) { status.textContent = "Error loading graph."; status.style.color = "#f87171"; }
  } finally {
    btn.disabled = false;
    btn.textContent = "Analyze";
  }
}

// ===== Stats Panel =====

function renderStats(s) {
  if (s.error) return;
  const fmt = n => n >= 1e9 ? (n/1e9).toFixed(2)+"B"
                 : n >= 1e6 ? (n/1e6).toFixed(2)+"M"
                 : n >= 1e3 ? (n/1e3).toFixed(1)+"K"
                 : n.toLocaleString();
  let panel = document.getElementById("stats-panel");
  if (!panel) {
    panel = document.createElement("div");
    panel.id = "stats-panel";
    panel.style.cssText = [
      "position:fixed","bottom:20px","right:20px",
      "background:rgba(15,23,42,0.95)","border:1px solid rgba(148,163,184,0.15)",
      "padding:16px 20px","border-radius:12px","z-index:1001",
      "backdrop-filter:blur(15px)","min-width:200px",
      "box-shadow:0 8px 32px rgba(0,0,0,0.4)","color:#e2e8f0"
    ].join(";");
    document.body.appendChild(panel);
  }
  panel.innerHTML = `
    <div style="font-size:11px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:10px">Dataset</div>
    <div class="stat-row"><span>Period</span><span>${s.first_tx} → ${s.last_tx}</span></div>
    <div class="stat-row"><span>Transfers</span><span>${fmt(s.total_transfers)}</span></div>
    <div class="stat-row" title="Unique wallets that sent at least one transfer"><span>Unique Senders</span><span>${fmt(s.unique_senders)}</span></div>
    <div class="stat-row" title="Unique wallets that received at least one transfer"><span>Unique Receivers</span><span>${fmt(s.unique_receivers)}</span></div>
    <div class="stat-row" title="Total token amount transferred (sum of all transfer values)"><span>Total Volume</span><span>${fmt(s.total_volume)}</span></div>
  `;
}

// ===== Render D3 Graph =====

// ===== Entity Color =====

function nodeColor(d) {
  if (d.is_x402) return "#f59e0b";
  const classes = d.entity_classes || [];
  if (classes.includes("BRIDGE")) return "#a78bfa";
  if (classes.includes("CEX"))    return "#34d399";
  return "#60a5fa";
}

function nodeLabel(d) {
  if (d.is_x402) return "x402 Agent";
  const classes = d.entity_classes || [];
  if (classes.includes("BRIDGE")) return "Bridge";
  if (classes.includes("CEX"))    return "CEX";
  return "Wallet";
}

// ===== Render D3 Graph =====

function renderGraph(data) {
  const nodes = data.nodes;
  const links = data.edges;

  // Assign rank index (nodes are already sorted by score desc from API)
  nodes.forEach((d, i) => { d.rank = i + 1; });

  const maxTx = d3.max(links, d => d.tx_count) || 1;
  const edgeWidth = d3.scaleLinear().domain([1, maxTx]).range([0.5, 4]).clamp(true);

  // Clear previous graph
  svg.selectAll("*").remove();

  const width = window.innerWidth;
  const height = window.innerHeight;
  svg.attr("viewBox", `0 0 ${width} ${height}`);

  const zoomLayer = svg.append("g");
  svg.call(d3.zoom()
    .scaleExtent([0.1, 10])
    .on("zoom", e => zoomLayer.attr("transform", e.transform))
  );

  const nodeRadius = d => Math.max(5, Math.sqrt(d.score) * 400);

  simulation = d3.forceSimulation(nodes)
    .alphaDecay(0.04)
    .velocityDecay(0.55)
    .force("link", d3.forceLink(links)
      .id(d => d.address)
      .distance(60)
      .strength(0.15)
    )
    .force("charge", d3.forceManyBody()
      .strength(d => -80 - nodeRadius(d) * 8)
      .distanceMax(400)
    )
    .force("center", d3.forceCenter(width / 2, height / 2).strength(0.05))
    .force("collision", d3.forceCollide()
      .radius(d => nodeRadius(d) + 3)
      .strength(0.8)
    )
    .on("end", () => simulation.stop());

  // Define arrow marker for directed edges
  const defs = svg.append("defs");
  defs.append("marker")
    .attr("id", "arrowhead")
    .attr("markerWidth", 8)
    .attr("markerHeight", 8)
    .attr("refX", 8)
    .attr("refY", 4)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,0L8,4L0,8Z")
    .attr("fill", "#94a3b8");

  // Render links
  const linkGroup = zoomLayer.append("g").attr("class", "links");
  const link = linkGroup
    .selectAll("line")
    .data(links)
    .enter()
    .append("line")
    .attr("class", "link")
    .attr("stroke-width", d => edgeWidth(d.tx_count || 1))
    .attr("marker-end", "url(#arrowhead)");

  // Render nodes
  const nodeGroup = zoomLayer.append("g").attr("class", "nodes");
  const node = nodeGroup
    .selectAll("circle")
    .data(nodes)
    .enter()
    .append("circle")
    .attr("class", "node")
    .attr("r", d => nodeRadius(d))
    .attr("fill", d => nodeColor(d))
    .attr("opacity", 0.85)
    .call(d3.drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended)
    );

  // Hover tooltip
  const tooltip = d3.select("#tooltip");
  node
    .on("mouseover", (event, d) => {
      tooltip
        .style("display", "block")
        .html(`
          <div style="font-size:11px;color:#94a3b8;margin-bottom:4px">${nodeLabel(d)}</div>
          <div style="font-family:monospace;font-size:11px;word-break:break-all">${d.address}</div>
          <div style="margin-top:6px;font-size:11px;color:#94a3b8">Rank: <span style="color:#e2e8f0">#${d.rank} of ${nodes.length}</span></div>
        `);
    })
    .on("mousemove", (event) => {
      const x = event.clientX + 14;
      const y = event.clientY - 10;
      tooltip.style("left", x + "px").style("top", y + "px");
    })
    .on("mouseout", () => tooltip.style("display", "none"));

  // Legend with counts
  const counts = { "Wallet": 0, "CEX": 0, "Bridge": 0, "x402 Agent": 0 };
  nodes.forEach(d => counts[nodeLabel(d)]++);

  const legend = svg.append("g").attr("transform", `translate(${width - 175}, 20)`);
  const legendItems = [
    { label: "Wallet",     color: "#60a5fa" },
    { label: "CEX",        color: "#34d399" },
    { label: "Bridge",     color: "#a78bfa" },
    { label: "x402 Agent", color: "#f59e0b" },
  ];
  legend.append("rect")
    .attr("x", -10).attr("y", -10)
    .attr("width", 165).attr("height", legendItems.length * 22 + 10)
    .attr("rx", 8)
    .attr("fill", "rgba(15,23,42,0.85)");
  legendItems.forEach((item, i) => {
    const g = legend.append("g").attr("transform", `translate(0, ${i * 22})`);
    g.append("circle").attr("r", 6).attr("cx", 6).attr("cy", 6).attr("fill", item.color);
    g.append("text").attr("x", 18).attr("y", 11)
      .attr("fill", "#e2e8f0").attr("font-size", "12px")
      .text(`${item.label} (${counts[item.label]})`);
  });

  // Update positions on simulation tick
  simulation.on("tick", () => {
    link
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => {
        const dx = d.target.x - d.source.x, dy = d.target.y - d.source.y;
        const dist = Math.sqrt(dx*dx + dy*dy);
        return dist === 0 ? d.target.x : d.target.x - (dx / dist) * nodeRadius(d.target);
      })
      .attr("y2", d => {
        const dx = d.target.x - d.source.x, dy = d.target.y - d.source.y;
        const dist = Math.sqrt(dx*dx + dy*dy);
        return dist === 0 ? d.target.y : d.target.y - (dy / dist) * nodeRadius(d.target);
      });

    node
      .attr("cx", d => d.x)
      .attr("cy", d => d.y);
  });

  // Drag handlers
  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }

  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }

  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }

  // Handle window resize
  window.addEventListener("resize", () => {
    const newWidth = window.innerWidth;
    const newHeight = window.innerHeight;
    svg.attr("viewBox", `0 0 ${newWidth} ${newHeight}`);
    if (simulation) {
      simulation.force("center", d3.forceCenter(newWidth / 2, newHeight / 2));
    }
  });
}

// ===== Error Display =====

function showError(message) {
  console.error(message);
  let toast = document.getElementById("error-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "error-toast";
    toast.style.cssText = [
      "position:fixed", "bottom:20px", "left:50%", "transform:translateX(-50%)",
      "background:rgba(239,68,68,0.15)", "border:1px solid rgba(239,68,68,0.4)",
      "color:#fca5a5", "padding:10px 18px", "border-radius:8px",
      "font-size:13px", "z-index:9999", "backdrop-filter:blur(10px)",
      "max-width:400px", "text-align:center"
    ].join(";");
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.style.display = "block";
  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(() => { toast.style.display = "none"; }, 5000);
}

// ===== Event Listeners =====

document.getElementById("network").addEventListener("change", () => {
  updateAssetDropdown();
});

document.getElementById("refresh").addEventListener("click", loadGraph);

// Allow Enter key to load graph
document.getElementById("topN").addEventListener("keypress", (e) => {
  if (e.key === "Enter") loadGraph();
});

// ===== Initialize =====

loadMeta();