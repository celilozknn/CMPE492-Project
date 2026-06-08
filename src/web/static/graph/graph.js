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
    
    // Load graph on first load
    loadGraph();
  } catch (error) {
    console.error("Error loading metadata:", error);
    showError("Failed to load network configuration");
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
  const compatibleAssets = Object.entries(META.compatibility)
    .filter(([_, networks]) => networks.includes(selectedNetwork))
    .map(([asset, _]) => asset);

  tokenSelect.innerHTML = `
    <option value="">All assets</option>
    ${compatibleAssets
      .map(asset => `<option value="${asset}">${asset}</option>`)
      .join("")}
  `;
}

// ===== Load and Render Graph =====

async function loadGraph() {
  try {
    const network = document.getElementById("network").value;
    const token = document.getElementById("token").value || "";
    const topN = document.getElementById("topN").value;

    if (!network) {
      showError("Please select a network");
      return;
    }

    // Build API URL
    const params = new URLSearchParams({
      network: network,
      top_n: topN
    });

    if (token) {
      params.append("token", token);
    }

    const url = `/api/graph?${params.toString()}`;

    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();

    if (!data.nodes || data.nodes.length === 0) {
      showError("No data available for selected filters");
      return;
    }

    currentGraph = data;
    renderGraph(data);
  } catch (error) {
    console.error("Error loading graph:", error);
    showError("Failed to load graph data. Check your API connection.");
  }
}

// ===== Render D3 Graph =====

function renderGraph(data) {
  const nodes = data.nodes;
  const links = data.edges;

  // Color scale based on PageRank score
  const color = d3.scaleSequential()
    .domain(d3.extent(nodes, d => d.score))
    .interpolator(d3.interpolatePlasma);

  // Clear previous graph
  svg.selectAll("*").remove();

  // Set viewBox to window dimensions
  const width = window.innerWidth;
  const height = window.innerHeight;
  svg.attr("viewBox", `0 0 ${width} ${height}`);

  // Initialize force simulation
  simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links)
      .id(d => d.address)
      .distance(80)
      .strength(0.3)
    )
    .force("charge", d3.forceManyBody()
      .strength(-150)
      .distanceMax(500)
    )
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide()
      .radius(d => Math.max(6, d.score * 2500) + 2)
    );

  // Define arrow marker for directed edges
  const defs = svg.append("defs");
  defs.append("marker")
    .attr("id", "arrowhead")
    .attr("markerWidth", 10)
    .attr("markerHeight", 10)
    .attr("refX", 20)
    .attr("refY", 0)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,-5L10,0L0,5")
    .attr("fill", "#64748b")
    .attr("opacity", 0.6);

  // Render links
  const linkGroup = svg.append("g").attr("class", "links");
  const link = linkGroup
    .selectAll("line")
    .data(links)
    .enter()
    .append("line")
    .attr("class", "link")
    .attr("marker-end", "url(#arrowhead)");

  // Render nodes
  const nodeGroup = svg.append("g").attr("class", "nodes");
  const node = nodeGroup
    .selectAll("circle")
    .data(nodes)
    .enter()
    .append("circle")
    .attr("class", "node")
    .attr("r", d => Math.max(6, d.score * 2500))
    .attr("fill", d => color(d.score))
    .attr("opacity", 0.85)
    .call(d3.drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended)
    );

  // Add tooltips
  node.append("title")
    .text(d => `${d.address}\nPageRank: ${d.score.toFixed(8)}`);

  // Update positions on simulation tick
  simulation.on("tick", () => {
    link
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);

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
  // Could add toast notification here
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