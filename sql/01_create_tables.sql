-- Parent transfers table
CREATE TABLE transfers (
    id BIGSERIAL NOT NULL,
    log_index INT NOT NULL,
    tx_index INT NOT NULL,
    tx_hash VARCHAR(66) NOT NULL,
    block_hash VARCHAR(66) NOT NULL,
    block_number BIGINT NOT NULL,
    block_timestamp BIGINT,
    network VARCHAR(20) NOT NULL,
    token_symbol VARCHAR(10) NOT NULL,
    token_address VARCHAR(42) NOT NULL,
    topic VARCHAR(66) NOT NULL,
    from_address VARCHAR(42) NOT NULL,
    to_address VARCHAR(42) NOT NULL,
    raw_value NUMERIC(78, 0) NOT NULL,
    value NUMERIC(38, 18) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tx_hash, log_index, network)  -- include partition key
) PARTITION BY LIST (network);

-- Ethereum partition
CREATE TABLE transfers_ethereum PARTITION OF transfers
    FOR VALUES IN ('ETHEREUM');

-- Arbitrum partition
CREATE TABLE transfers_arbitrum PARTITION OF transfers
    FOR VALUES IN ('ARBITRUM');

-- Polygon partition
CREATE TABLE transfers_polygon PARTITION OF transfers
    FOR VALUES IN ('POLYGON');

-- Avalanche partition
CREATE TABLE transfers_avalanche PARTITION OF transfers
    FOR VALUES IN ('AVALANCHE');

-- Optimism partition
CREATE TABLE transfers_optimism PARTITION OF transfers
    FOR VALUES IN ('OPTIMISM');
    
-- Fetch progress table ""
CREATE TABLE fetch_progress (
    id SERIAL PRIMARY KEY,
    network VARCHAR(20) NOT NULL,
    chunk_start BIGINT NOT NULL,
    chunk_end BIGINT NOT NULL,
    log_count INT NOT NULL,
    completed_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(network, chunk_start, chunk_end)
);