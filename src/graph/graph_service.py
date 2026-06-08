from src.graph.queries import EDGE_LIST_QUERY, EDGE_LIST_BY_TOKEN_QUERY
from src.graph.pagerank import build_graph, compute_pagerank
from src.db import upsert_pagerank_scores, get_connection


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
    
    # save to db
    if save:
        logger.info("Saving PageRank to DB...")

        upsert_pagerank_scores(
            network=network.value,  
            token_symbol=token_symbol,
            ranks=ranks
        )

        logger.info("✓ PageRank saved to DB")

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
            cur.execute(query, (network.upper(), token_symbol, token_symbol, limit))
            return cur.fetchall()

def get_edges(network: str, token_symbol: str | None, nodes: list[str]):
    query = """
                SELECT from_address, to_address
                FROM transfers
                WHERE network = %s
                AND (%s IS NULL OR token_symbol = %s)
                AND from_address = ANY(%s)
                AND to_address = ANY(%s)
            """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (network.upper(), token_symbol, token_symbol, nodes, nodes))
            return cur.fetchall()
        