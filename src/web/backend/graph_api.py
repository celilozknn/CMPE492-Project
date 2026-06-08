import logging
from fastapi import APIRouter, Query
from src.db import get_connection
from src.graph.graph_service import get_pagerank_scores, get_edges, get_node_labels, run_pagerank_graph
from src.enums import Networks

router = APIRouter()
logger = logging.getLogger("graph_api")


@router.get("/api/stats")
def stats(network: str = Query("ethereum"), token: str | None = None):
    from datetime import datetime, timezone
    query = """
        SELECT
            MIN(block_timestamp)            AS first_ts,
            MAX(block_timestamp)            AS last_ts,
            COUNT(*)                        AS total_transfers,
            COUNT(DISTINCT from_address)    AS unique_senders,
            COUNT(DISTINCT to_address)      AS unique_receivers,
            COALESCE(SUM(value), 0)         AS total_volume
        FROM transfers
        WHERE network = %s
        AND (%s IS NULL OR token_symbol = %s)
    """
    from src.db import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (network.upper(), token, token))
            row = cur.fetchone()

    if not row or not row["first_ts"]:
        return {"error": "No data"}

    def fmt_ts(ts):
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")

    return {
        "first_tx":         fmt_ts(row["first_ts"]),
        "last_tx":          fmt_ts(row["last_ts"]),
        "total_transfers":  int(row["total_transfers"]),
        "unique_senders":   int(row["unique_senders"]),
        "unique_receivers": int(row["unique_receivers"]),
        "total_volume":     float(row["total_volume"]),
    }
    
@router.get("/api/graph")
def graph(
    network: str = Query("ethereum"),
    token: str | None = None,
    top_n: int = Query(100, ge=1, le=1000)
):
    # Normalize network name (e.g., "Optimism" -> "optimism")
    network_lower = network.lower()
    
    # Map to Networks enum
    try:
        network_enum = Networks[network_lower.upper()]
    except KeyError:
        return {
            "nodes": [],
            "edges": [],
            "error": f"Unknown network: {network}"
        }
    
    # Try to fetch existing pagerank scores
    nodes_raw = get_pagerank_scores(network_lower, token, top_n)

    # If no data found, compute pagerank on-demand
    if not nodes_raw:
        logger.info(f"No pagerank data for {network_lower}/{token}. Computing...")
        try:
            run_pagerank_graph(
                network=network_enum,
                token_symbol=token,
                top_n=top_n,
                logger=logger,
                save=True
            )
            # Fetch the newly computed scores
            nodes_raw = get_pagerank_scores(network_lower, token, top_n)
        except Exception as e:
            logger.error(f"Error computing pagerank: {e}")
            return {
                "nodes": [],
                "edges": [],
                "error": f"No data available. Graph computation failed: {str(e)}"
            }

    nodes = [
        {"address": r["address"], "score": float(r["score"])}
        for r in nodes_raw
    ]

    node_addresses = [n["address"] for n in nodes]
    edges_raw = get_edges(network_lower, token, node_addresses)
    labels = get_node_labels(network_lower, token, node_addresses)

    for node in nodes:
        info = labels.get(node["address"], {})
        node["entity_classes"] = info.get("entity_classes", [])
        node["is_x402"] = info.get("is_x402", False)

    edges = [
        {"source": e["from_address"], "target": e["to_address"], "tx_count": e["tx_count"]}
        for e in edges_raw
    ]

    return {
        "nodes": nodes,
        "edges": edges
    }