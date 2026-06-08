from graph.queries import EDGE_LIST_QUERY, EDGE_LIST_BY_TOKEN_QUERY
from graph.pagerank import build_graph, compute_pagerank
from db import upsert_pagerank_scores, get_connection


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