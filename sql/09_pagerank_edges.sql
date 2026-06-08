CREATE TABLE IF NOT EXISTS pagerank_edges (
    id BIGSERIAL PRIMARY KEY,
    network TEXT NOT NULL,
    token_symbol TEXT,
    from_address TEXT NOT NULL,
    to_address TEXT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_pagerank_edges
        UNIQUE (network, token_symbol, from_address, to_address)
);

CREATE INDEX idx_pagerank_edges_lookup
ON pagerank_edges (network, token_symbol);
