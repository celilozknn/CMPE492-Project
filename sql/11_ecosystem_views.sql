-- Index to make is_from_x402 = true filters fast
CREATE INDEX IF NOT EXISTS idx_is_from_x402
ON transfers (network, is_from_x402)
WHERE is_from_x402 = true;

-- Also missing: GIN index on from_entity_class text[] for @> containment queries
CREATE INDEX IF NOT EXISTS idx_from_entity_class_gin
ON transfers USING GIN (from_entity_class);

-- ── Materialized view 1: entity segment aggregates ──────────────────────────
-- Pre-computes volume + tx count per (network, token_symbol, segment).
-- segment is derived from is_from_x402 > CEX > BRIDGE > Regular.
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_ecosystem_segments AS
SELECT
    network,
    token_symbol,
    CASE
        WHEN is_from_x402 = true               THEN 'x402 Agent'
        WHEN from_entity_class @> ARRAY['CEX'] THEN 'CEX'
        WHEN from_entity_class @> ARRAY['BRIDGE'] THEN 'Bridge'
        ELSE 'Regular Wallet'
    END AS segment,
    COUNT(*)   AS tx_count,
    SUM(value) AS volume
FROM transfers
GROUP BY network, token_symbol, segment;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_ecosystem_segments
ON mv_ecosystem_segments (network, token_symbol, segment);

-- ── Materialized view 2: x402 token breakdown ────────────────────────────────
-- Volume + tx count per token for x402-origin transfers.
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_ecosystem_x402_tokens AS
SELECT
    network,
    token_symbol,
    COUNT(*)   AS tx_count,
    SUM(value) AS volume
FROM transfers
WHERE is_from_x402 = true
GROUP BY network, token_symbol;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_ecosystem_x402_tokens
ON mv_ecosystem_x402_tokens (network, token_symbol);

-- ── Materialized view 3: x402 monthly timeline ───────────────────────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_ecosystem_x402_timeline AS
SELECT
    network,
    token_symbol,
    to_char(to_timestamp(block_timestamp), 'YYYY-MM') AS period,
    COUNT(*)   AS tx_count,
    SUM(value) AS volume
FROM transfers
WHERE is_from_x402 = true
GROUP BY network, token_symbol, period;

CREATE INDEX IF NOT EXISTS idx_mv_ecosystem_x402_timeline
ON mv_ecosystem_x402_timeline (network, token_symbol, period);

-- ── Materialized view 4: top x402 agents ────────────────────────────────────
-- Per-agent totals + their highest-volume token, used for the leaderboard table.
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_ecosystem_x402_agents AS
SELECT
    network,
    from_address                                      AS address,
    COUNT(*)                                          AS tx_count,
    SUM(value)                                        AS volume,
    (
        SELECT token_symbol
        FROM transfers t2
        WHERE t2.network = t.network
          AND t2.from_address = t.from_address
          AND t2.is_from_x402 = true
        GROUP BY token_symbol
        ORDER BY SUM(value) DESC
        LIMIT 1
    )                                                 AS top_token
FROM transfers t
WHERE is_from_x402 = true
GROUP BY network, from_address;

CREATE INDEX IF NOT EXISTS idx_mv_ecosystem_x402_agents
ON mv_ecosystem_x402_agents (network, volume DESC);