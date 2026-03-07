CREATE TABLE transfers (
    id SERIAL PRIMARY KEY,
    log_index INT NOT NULL,
    tx_index INT NOT NULL,
    tx_hash CHAR(66) NOT NULL,
    block_hash CHAR(66) NOT NULL,
    block_number BIGINT NOT NULL,
    block_timestamp TIMESTAMP NOT NULL,
    token_address CHAR(42) NOT NULL,
    token_symbol VARCHAR(10),
    topic CHAR(66) NOT NULL,
    from_address CHAR(42) NOT NULL,
    to_address CHAR(42) NOT NULL,
    raw_value NUMERIC(38,0) NOT NULL,
    value NUMERIC(38,18) NOT NULL,
    raw_log JSONB
);

CREATE INDEX idx_tx_hash ON transfers(tx_hash);
CREATE INDEX idx_block_number ON transfers(block_number);
CREATE INDEX idx_from_to ON transfers(from_address, to_address);