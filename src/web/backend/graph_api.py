from fastapi import APIRouter, Query
from src.db import get_connection
from src.graph.graph_service import get_pagerank_scores, get_edges

router = APIRouter()

from fastapi import Query
    
@router.get("/api/graph")
def graph(
    network: str = Query("ethereum"),
    token: str | None = None,
    top_n: int = Query(50, ge=1, le=500)
):
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