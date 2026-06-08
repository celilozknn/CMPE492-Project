from fastapi import APIRouter, Query
from src.db import get_connection

router = APIRouter()


@router.get("/api/ecosystem/overview")
def ecosystem_overview(
    network: str = Query("ethereum"),
    token: str | None = None,
):
    network = network.upper()
    tok = token if token else None

    query = """
        SELECT segment, SUM(tx_count) AS tx_count, SUM(volume) AS volume
        FROM mv_ecosystem_segments
        WHERE network = %s
          AND (%s IS NULL OR token_symbol = %s)
        GROUP BY segment
        ORDER BY volume DESC
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (network, tok, tok))
            rows = cur.fetchall()

    segments = [
        {
            "label":    row["segment"],
            "tx_count": int(row["tx_count"]),
            "volume":   float(row["volume"]),
        }
        for row in rows
    ]
    total_volume = sum(s["volume"] for s in segments)
    total_txs    = sum(s["tx_count"] for s in segments)

    return {
        "segments":     segments,
        "total_volume": total_volume,
        "total_txs":    total_txs,
    }


@router.get("/api/ecosystem/token-breakdown")
def ecosystem_token_breakdown(
    network: str = Query("ethereum"),
):
    network = network.upper()

    query = """
        SELECT token_symbol, SUM(tx_count) AS tx_count, SUM(volume) AS volume
        FROM mv_ecosystem_x402_tokens
        WHERE network = %s
        GROUP BY token_symbol
        ORDER BY volume DESC
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (network,))
            rows = cur.fetchall()

    return [
        {
            "token":    row["token_symbol"],
            "tx_count": int(row["tx_count"]),
            "volume":   float(row["volume"]),
        }
        for row in rows
    ]


@router.get("/api/ecosystem/x402-timeline")
def ecosystem_x402_timeline(
    network: str = Query("ethereum"),
    token: str | None = None,
):
    network = network.upper()
    tok = token if token else None

    query = """
        SELECT period, SUM(tx_count) AS tx_count, SUM(volume) AS volume
        FROM mv_ecosystem_x402_timeline
        WHERE network = %s
          AND (%s IS NULL OR token_symbol = %s)
        GROUP BY period
        ORDER BY period
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (network, tok, tok))
            rows = cur.fetchall()

    return [
        {
            "period":   row["period"],
            "tx_count": int(row["tx_count"]),
            "volume":   float(row["volume"]),
        }
        for row in rows
    ]


@router.get("/api/ecosystem/top-agents")
def ecosystem_top_agents(
    network: str = Query("ethereum"),
    limit: int = Query(20, ge=1, le=100),
):
    network = network.upper()

    query = """
        SELECT address, tx_count, volume, top_token
        FROM mv_ecosystem_x402_agents
        WHERE network = %s
        ORDER BY volume DESC
        LIMIT %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (network, limit))
            rows = cur.fetchall()

    return [
        {
            "address":   row["address"],
            "tx_count":  int(row["tx_count"]),
            "volume":    float(row["volume"]),
            "top_token": row["top_token"],
        }
        for row in rows
    ]


@router.post("/api/ecosystem/refresh")
def ecosystem_refresh():
    """Refresh materialized views. Run after new data ingestion or re-classification."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_ecosystem_segments")
            cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_ecosystem_x402_tokens")
            cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_ecosystem_x402_timeline")
            cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_ecosystem_x402_agents")
        conn.commit()
    return {"status": "ok"}
