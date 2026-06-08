
# PageRank queries
EDGE_LIST_QUERY = """
SELECT
    from_address,
    to_address,
    SUM(value) AS weight,
    COUNT(*) AS tx_count
FROM transfers
WHERE network = %s
GROUP BY from_address, to_address
"""

EDGE_LIST_BY_TOKEN_QUERY = """
SELECT
    from_address,
    to_address,
    SUM(value) AS weight,
    COUNT(*) AS tx_count
FROM transfers
WHERE network = %s AND token_symbol = %s
GROUP BY from_address, to_address
"""