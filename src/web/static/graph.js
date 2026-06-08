const svg = d3.select("svg");

let simulation;

async function loadGraph() {
    const network = document.getElementById("network").value;
    const token = document.getElementById("token").value || "";
    const top_n = document.getElementById("topN").value;

    const url = `/graph?network=${network}&top_n=${top_n}` + (token ? `&token=${token}` : "");

    const res = await fetch(url);
    const data = await res.json();

    const nodes = data.nodes;
    const links = data.edges;

    svg.selectAll("*").remove();

    simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(d => d.address).distance(60))
        .force("charge", d3.forceManyBody().strength(-80))
        .force("center", d3.forceCenter(window.innerWidth / 2, window.innerHeight / 2));

    const link = svg.append("g")
        .selectAll("line")
        .data(links)
        .enter()
        .append("line")
        .attr("class", "link");

    const node = svg.append("g")
        .selectAll("circle")
        .data(nodes)
        .enter()
        .append("circle")
        .attr("class", "node")
        .attr("r", d => Math.max(4, d.score * 2000))
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

    node.append("title")
        .text(d => `${d.address}\nscore: ${d.score}`);

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

document.getElementById("refresh").onclick = loadGraph;

loadGraph();