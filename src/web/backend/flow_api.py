from fastapi import APIRouter, Query
from src.db import get_connection
from datetime import datetime, timezone

router = APIRouter()


def _token(t: str | None) -> str | None:
    return t if t else None


def fmt_ts(ts):
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


@router.get("/api/flow/summary")
def flow_summary(
    address: str = Query(...),
    network: str = Query("ethereum"),
    token: str | None = None,
):
    address = address.lower()
    network = network.upper()
    token = _token(token)

    query = """
        SELECT
            COUNT(*) FILTER (WHERE from_address = %s)           AS sent_count,
            COUNT(*) FILTER (WHERE to_address = %s)             AS recv_count,
            COALESCE(SUM(value) FILTER (WHERE from_address = %s), 0) AS sent_volume,
            COALESCE(SUM(value) FILTER (WHERE to_address = %s), 0)   AS recv_volume,
            MIN(block_timestamp)                                 AS first_seen,
            MAX(block_timestamp)                                 AS last_seen,
            COUNT(DISTINCT token_symbol)                         AS token_count,
            MAX(from_entity_class) FILTER (WHERE from_address = %s) AS entity_class,
            BOOL_OR(is_from_x402) FILTER (WHERE from_address = %s)  AS is_x402
        FROM transfers
        WHERE network = %s
        AND (%s IS NULL OR token_symbol = %s)
        AND (from_address = %s OR to_address = %s)
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (
                address, address, address, address,
                address, address,
                network, token, token,
                address, address,
            ))
            row = cur.fetchone()

    if not row or (not row["sent_count"] and not row["recv_count"]):
        return {"error": "No transfers found for this address"}

    return {
        "address":      address,
        "sent_count":   int(row["sent_count"] or 0),
        "recv_count":   int(row["recv_count"] or 0),
        "sent_volume":  float(row["sent_volume"] or 0),
        "recv_volume":  float(row["recv_volume"] or 0),
        "net_flow":     float((row["recv_volume"] or 0) - (row["sent_volume"] or 0)),
        "first_seen":   fmt_ts(row["first_seen"]),
        "last_seen":    fmt_ts(row["last_seen"]),
        "entity_class": row["entity_class"] or [],
        "is_x402":      bool(row["is_x402"]),
    }


_SORT_COLS = {
    "timestamp": "block_timestamp",
    "value":     "value",
    "token":     "token_symbol",
    "direction": "CASE WHEN from_address = %s THEN 'sent' ELSE 'received' END",
}

@router.get("/api/flow/transfers")
def flow_transfers(
    address: str = Query(...),
    network: str = Query("ethereum"),
    token: str | None = None,
    direction: str = Query("all"),   # all | sent | received
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("timestamp"),
    sort_order: str = Query("desc"),
    counterparty: str | None = None,
):
    address = address.lower()
    network = network.upper()
    token = _token(token)
    cp = counterparty.lower() if counterparty else None

    if cp:
        addr_filter = "((from_address = %s AND to_address = %s) OR (from_address = %s AND to_address = %s))"
        params_addr = (address, cp, cp, address)
    elif direction == "sent":
        addr_filter = "from_address = %s"
        params_addr = (address,)
    elif direction == "received":
        addr_filter = "to_address = %s"
        params_addr = (address,)
    else:
        addr_filter = "(from_address = %s OR to_address = %s)"
        params_addr = (address, address)

    sort_col = _SORT_COLS.get(sort_by, "block_timestamp")
    order = "DESC" if sort_order.lower() != "asc" else "ASC"

    # direction sort col needs the address substituted inline
    if sort_by == "direction":
        order_clause = f"CASE WHEN from_address = '{address}' THEN 'sent' ELSE 'received' END {order}"
    else:
        order_clause = f"{sort_col} {order}"

    query = f"""
        SELECT
            tx_hash,
            block_timestamp,
            token_symbol,
            from_address,
            to_address,
            value,
            CASE WHEN from_address = %s THEN 'sent' ELSE 'received' END AS direction
        FROM transfers
        WHERE network = %s
        AND (%s IS NULL OR token_symbol = %s)
        AND {addr_filter}
        ORDER BY {order_clause}
        LIMIT %s OFFSET %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (address, network, token, token, *params_addr, limit, offset))
            rows = cur.fetchall()

    return [
        {
            "tx_hash":    row["tx_hash"],
            "timestamp":  fmt_ts(row["block_timestamp"]),
            "token":      row["token_symbol"],
            "from":       row["from_address"],
            "to":         row["to_address"],
            "value":      float(row["value"]),
            "direction":  row["direction"],
        }
        for row in rows
    ]


@router.get("/api/flow/counterparties")
def flow_counterparties(
    address: str = Query(...),
    network: str = Query("ethereum"),
    token: str | None = None,
    limit: int = Query(10, ge=1, le=50),
):
    address = address.lower()
    network = network.upper()
    token = _token(token)

    query = """
        SELECT * FROM (
            SELECT
                counterparty,
                COALESCE(SUM(volume) FILTER (WHERE relation = 'sent'),     0) AS sent_volume,
                COALESCE(SUM(volume) FILTER (WHERE relation = 'received'), 0) AS recv_volume,
                COALESCE(SUM(tx_count) FILTER (WHERE relation = 'sent'),     0) AS sent_txs,
                COALESCE(SUM(tx_count) FILTER (WHERE relation = 'received'), 0) AS recv_txs
            FROM (
                SELECT to_address   AS counterparty, SUM(value) AS volume, COUNT(*) AS tx_count, 'sent'     AS relation
                FROM transfers
                WHERE network = %s AND (%s IS NULL OR token_symbol = %s) AND from_address = %s
                GROUP BY to_address

                UNION ALL

                SELECT from_address AS counterparty, SUM(value) AS volume, COUNT(*) AS tx_count, 'received' AS relation
                FROM transfers
                WHERE network = %s AND (%s IS NULL OR token_symbol = %s) AND to_address = %s
                GROUP BY from_address
            ) sub
            GROUP BY counterparty
        ) agg
        ORDER BY (sent_volume + recv_volume) DESC
        LIMIT %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (
                network, token, token, address,
                network, token, token, address,
                limit,
            ))
            rows = cur.fetchall()

    return [
        {
            "address":      row["counterparty"],
            "sent_volume":  float(row["sent_volume"]),
            "recv_volume":  float(row["recv_volume"]),
            "sent_txs":     int(row["sent_txs"]),
            "recv_txs":     int(row["recv_txs"]),
        }
        for row in rows
    ]


@router.get("/api/flow/sample")
def flow_sample(
    network: str = Query("ethereum"),
    token: str | None = None,
    count: int = Query(5, ge=1, le=20),
):
    """Returns addresses with significant activity, randomly sampled from top 500 by tx count."""
    network = network.upper()
    token = _token(token)

    query = """
        SELECT address, tx_count
        FROM top_wallets
        WHERE network = %s
        AND (%s IS NULL OR token_symbol = %s)
        AND tx_count >= 50
        ORDER BY RANDOM()
        LIMIT %s
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (network.lower(), token, token, count))
            rows = cur.fetchall()

    return [
        {"address": row["address"], "tx_count": int(row["tx_count"])}
        for row in rows
    ]
