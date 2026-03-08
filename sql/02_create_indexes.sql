CREATE INDEX idx_block_number ON transfers(block_number);
CREATE INDEX idx_block_timestamp ON transfers(block_timestamp);
CREATE INDEX idx_from_address ON transfers(from_address);
CREATE INDEX idx_to_address ON transfers(to_address);
CREATE INDEX idx_token_symbol ON transfers(token_symbol);
CREATE INDEX idx_network ON transfers(network);
CREATE INDEX idx_token_network ON transfers(token_symbol, network);

CREATE INDEX idx_progress_network ON fetch_progress(network);