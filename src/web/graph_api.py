from fastapi import APIRouter, Query
from src.db import get_connection
from src.graph.graph_service import get_pagerank_scores, get_edges

router = APIRouter()


@router.get("/pagerank")
def pagerank(
    network: str,
    token: str | None = None,
    top_n: int = Query(default=100, ge=1, le=1000)
):
    rows = get_pagerank_scores(network, token, top_n)

    return {
        "nodes": [
            {"address": r["address"], "score": r["score"]}
            for r in rows
        ]
    }

@router.get("/graph")
def graph(network: str, token: str | None = None, top_n: int = 100):
    nodes_raw = get_pagerank_scores(network, token, top_n)

    nodes = [
        {"address": r["address"], "score": float(r["score"])}
        for r in nodes_raw
    ]

    node_addresses = [n["address"] for n in nodes]
    edges = get_edges(network, token, node_addresses)

    return {
        "nodes": nodes,
        "edges": edges
    }