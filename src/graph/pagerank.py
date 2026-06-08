import networkx as nx


def build_graph(edges):
    G = nx.DiGraph()

    for e in edges:
        if e["from_address"] == e["to_address"]:
            continue

        G.add_edge(
            e["from_address"],
            e["to_address"],
            weight=float(e["weight"])
        )

    return G


def compute_pagerank(G, damping=0.85):
    return nx.pagerank(G, alpha=damping, weight="weight")


def top_k(ranks: dict, k: int):
    return sorted(ranks.items(), key=lambda x: x[1], reverse=True)[:k]