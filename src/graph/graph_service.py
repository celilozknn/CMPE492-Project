from src.graph.queries import EDGE_LIST_QUERY, EDGE_LIST_BY_TOKEN_QUERY
from src.graph.pagerank import build_graph, compute_pagerank
from src.db import upsert_pagerank_scores, upsert_pagerank_edges, get_connection


# ----------------------------
# DATA LOADING
# ----------------------------
def load_edges(network, token_symbol=None):
    query = EDGE_LIST_QUERY if not token_symbol else EDGE_LIST_BY_TOKEN_QUERY

    params = [network.name]

    if token_symbol:
        params.append(token_symbol)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()


# ----------------------------
# MAIN PIPELINE
# ----------------------------
def run_pagerank_graph(network, token_symbol, top_n, logger, save=True):
    logger.info("Loading edges...")
    edges = load_edges(network, token_symbol)

    if not edges:
        logger.warning("No edges found")
        return {}

    logger.info(f"Loaded {len(edges):,} edges")

    logger.info("Building graph...")
    G = build_graph(edges)

    logger.info(f"Nodes={G.number_of_nodes():,}, Edges={G.number_of_edges():,}")

    logger.info("Computing PageRank...")
    ranks = compute_pagerank(G)

    logger.info(f"Computed ranks for {len(ranks):,} nodes")
    
    if save:
        MAX_NODES = 10_000
        top_ranks = dict(
            sorted(ranks.items(), key=lambda x: x[1], reverse=True)[:MAX_NODES]
        )
        top_addresses = set(top_ranks.keys())

        logger.info(f"Saving top {len(top_ranks):,} PageRank scores to DB...")
        upsert_pagerank_scores(
            network=network.value,
            token_symbol=token_symbol,
            ranks=top_ranks
        )

        logger.info("Saving PageRank edges to DB...")
        edge_pairs = [
            (u, v)
            for u, v in G.edges()
            if u in top_addresses and v in top_addresses
        ]
        upsert_pagerank_edges(
            network=network.value,
            token_symbol=token_symbol,
            edges=edge_pairs
        )

        logger.info(f"✓ PageRank saved: {len(top_ranks):,} scores, {len(edge_pairs):,} edges")

    return ranks

def get_pagerank_scores(network: str, token_symbol: str | None, limit: int):
    query = """
                SELECT address, score
                FROM pagerank_scores
                WHERE network = %s
                AND (%s IS NULL OR token_symbol = %s)
                ORDER BY score DESC
                LIMIT %s;
            """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (network.lower(), token_symbol, token_symbol, limit))
            return cur.fetchall()

def get_edges(network: str, token_symbol: str | None, nodes: list[str]):
    query = """
                SELECT pe.from_address, pe.to_address, COUNT(t.tx_hash) AS tx_count
                FROM pagerank_edges pe
                LEFT JOIN transfers t
                    ON t.network = pe.network
                    AND (%s IS NULL OR t.token_symbol = %s)
                    AND t.from_address = pe.from_address
                    AND t.to_address = pe.to_address
                WHERE pe.network = %s
                AND (%s IS NULL OR pe.token_symbol = %s)
                AND pe.from_address = ANY(%s)
                AND pe.to_address = ANY(%s)
                GROUP BY pe.from_address, pe.to_address
            """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (token_symbol, token_symbol, network.lower(), token_symbol, token_symbol, nodes, nodes))
            return cur.fetchall()


def get_node_labels(network: str, token_symbol: str | None, nodes: list[str]):
    """Returns entity classification for each node address."""
    query = """
                SELECT address, entity_classes, is_x402
                FROM (
                    SELECT from_address AS address,
                           from_entity_class AS entity_classes,
                           is_from_x402 AS is_x402
                    FROM transfers
                    WHERE network = %s
                    AND (%s IS NULL OR token_symbol = %s)
                    AND from_address = ANY(%s)
                    UNION
                    SELECT to_address,
                           to_entity_class,
                           is_to_x402
                    FROM transfers
                    WHERE network = %s
                    AND (%s IS NULL OR token_symbol = %s)
                    AND to_address = ANY(%s)
                ) sub
                WHERE entity_classes IS NOT NULL OR is_x402 = true
            """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (
                network.lower(), token_symbol, token_symbol, nodes,
                network.lower(), token_symbol, token_symbol, nodes,
            ))
            rows = cur.fetchall()

    labels = {}
    for row in rows:
        addr = row["address"]
        if addr not in labels:
            labels[addr] = {"entity_classes": set(), "is_x402": False}
        if row["entity_classes"]:
            labels[addr]["entity_classes"].update(row["entity_classes"])
        if row["is_x402"]:
            labels[addr]["is_x402"] = True

    return {
        addr: {
            "entity_classes": list(v["entity_classes"]),
            "is_x402": v["is_x402"]
        }
        for addr, v in labels.items()
    }
        