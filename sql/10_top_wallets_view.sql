CREATE MATERIALIZED VIEW IF NOT EXISTS top_wallets AS
SELECT
    p.network,
    p.token_symbol,
    p.address,
    p.score,
    COUNT(t.tx_hash) AS tx_count
FROM pagerank_scores p
JOIN transfers t
    ON t.from_address = p.address
    AND UPPER(p.network) = t.network
    AND (p.token_symbol IS NULL OR t.token_symbol = p.token_symbol)
GROUP BY p.network, p.token_symbol, p.address, p.score;

CREATE INDEX IF NOT EXISTS idx_top_wallets_lookup
ON top_wallets (network, token_symbol, tx_count DESC);
