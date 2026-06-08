CREATE TABLE IF NOT EXISTS pagerank_scores (
    id BIGSERIAL PRIMARY KEY,
    network TEXT NOT NULL,
    token_symbol TEXT,
    address TEXT NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_pagerank_scores
        UNIQUE (network, token_symbol, address)
);

CREATE INDEX idx_pagerank_lookup
ON pagerank_scores (network, token_symbol, score DESC);