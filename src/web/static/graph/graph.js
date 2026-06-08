const svg = d3.select("svg");
svg.attr("viewBox", `0 0 ${window.innerWidth} ${window.innerHeight}`);

let simulation;

async function loadGraph() {
    const network = document.getElementById("network").value;
    const token = document.getElementById("token").value || "";
    const top_n = document.getElementById("topN").value;

    const url = `api/graph?network=${network}&top_n=${top_n}` + (token ? `&token=${token}` : "");

    const res = await fetch(url);
    const data = await res.json();

    const nodes = data.nodes;
    const links = data.edges;

    const color = d3.scaleSequential()
        .domain(d3.extent(nodes, d => d.score))
        .interpolator(d3.interpolatePlasma);

    svg.selectAll("*").remove();

    simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(d => d.address).distance(70))
        .force("charge", d3.forceManyBody().strength(-120))
        .force("center", d3.forceCenter(window.innerWidth / 2, window.innerHeight / 2));

    // Arrow marker (flow direction)
    svg.append("defs").append("marker")
        .attr("id", "arrow")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 18)
        .attr("refY", 0)
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M0,-5L10,0L0,5")
        .attr("fill", "#6b7280");

    const link = svg.append("g")
        .selectAll("line")
        .data(links)
        .enter()
        .append("line")
        .attr("class", "link")
        .attr("marker-end", "url(#arrow)");

    const node = svg.append("g")
        .selectAll("circle")
        .data(nodes)
        .enter()
        .append("circle")
        .attr("class", "node")
        .attr("r", d => Math.max(4, d.score * 2000))
        .attr("fill", d => color(d.score))
        .attr("opacity", 0.9)
        .call(
            d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended)
        );

    node.append("title")
        .text(d => `${d.address}\nscore: ${d.score.toFixed(6)}`);

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
}

let META = {
    networks: [],
    stablecoins: [],
    compatibility: {}
};

async function loadMeta() {
    const [n, s, c] = await Promise.all([
        fetch("/meta/networks").then(r => r.json()),
        fetch("/meta/stablecoins").then(r => r.json()),
        fetch("/meta/compatibility").then(r => r.json())
    ]);

    META.networks = n.networks;
    META.stablecoins = s.stablecoins;
    META.compatibility = c;

    renderFilters();
}

function renderFilters() {
    const networkSelect = document.getElementById("network");
    const tokenSelect = document.getElementById("token");

    networkSelect.innerHTML = META.networks
        .map(n => `<option value="${n}">${n}</option>`)
        .join("");

    tokenSelect.innerHTML = `
        <option value="">all tokens</option>
        ${META.stablecoins.map(s =>
            `<option value="${s}">${s}</option>`
        ).join("")}
    `;

    networkSelect.onchange = filterTokens;
}

function filterTokens() {
    const network = document.getElementById("network").value;
    const tokenSelect = document.getElementById("token");

    const allowed = Object.entries(META.compatibility)
        .filter(([token, nets]) => nets.includes(network))
        .map(([token]) => token);

    tokenSelect.innerHTML = `
        <option value="">all tokens</option>
        ${allowed.map(t => `<option value="${t}">${t}</option>`).join("")}
    `;
}

loadMeta().then(loadGraph);
document.getElementById("refresh").onclick = loadGraph;