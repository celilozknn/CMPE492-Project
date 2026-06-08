import sys, os
import psycopg2
import dotenv
from psycopg2.extras import RealDictCursor, execute_values 

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.paths import *
from src.helpers import *
from src.enums import *

dotenv.load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "chainflow")
DB_USER = os.getenv("DB_USER", "chainflowuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "chainflowpass")

logger = get_logger("DB")

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor,
    )

# ----------------------------
# TRANSFERS
# ----------------------------
def insert_transfer(transfer: dict):
    query = """
    INSERT INTO transfers (
        log_index, tx_index, tx_hash, block_hash, block_number,
        block_timestamp, network, token_symbol, token_address,
        topic, from_address, to_address, raw_value, value
    ) VALUES (
        %(log_index)s, %(tx_index)s, %(tx_hash)s, %(block_hash)s, %(block_number)s,
        %(block_timestamp)s, %(network)s, %(token_symbol)s, %(token_address)s,
        %(topic)s, %(from)s, %(to)s, %(raw_value)s, %(value)s
    )
    ON CONFLICT (tx_hash, log_index, network) DO NOTHING;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, transfer)
            if cur.rowcount == 0:
                logger.warning(f"Transfer already exists, skipped: {transfer['tx_hash']}")
            else:
                conn.commit()
                logger.debug(f"Inserted transfer: {transfer['network']}, Block:{transfer['block_number']}, Log Index: {transfer['log_index']}, Tx: {transfer['tx_hash']},")

def insert_transfers_batch(transfers: list[dict], batch_size: int):
    if not transfers:
        return

    query = """
    INSERT INTO transfers (
        log_index, tx_index, tx_hash, block_hash, block_number,
        block_timestamp, network, token_symbol, token_address,
        topic, from_address, to_address, raw_value, value
    ) VALUES %s
    ON CONFLICT (tx_hash, log_index, network) DO NOTHING;
    """

    def to_tuple(t):
        return (
            t["log_index"], t["tx_index"], t["tx_hash"], t["block_hash"], t["block_number"],
            t["block_timestamp"], t["network"], t["token_symbol"], t["token_address"],
            t["topic"], t["from"], t["to"], t["raw_value"], t["value"]
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            for i in range(0, len(transfers), batch_size):
                batch = transfers[i:i + batch_size]

                execute_values(
                    cur,
                    query,
                    [to_tuple(t) for t in batch],
                    page_size=len(batch)  # prevents internal splitting confusion
                )

                conn.commit()

                logger.info(
                    f"Batch processed | size={len(batch)}"
                )
                          
def get_transfers(params: dict = None):
    """
    Flexible read: pass a dict with any subset of column filters, e.g.
    {"network": "ethereum", "token_symbol": "ETH"}
    Columns are: id, log_index, tx_index, tx_hash, block_hash, block_number, block_timestamp,
    network, token_symbol, token_address, topic, from_address, to_address, raw_value, value, created_at
    """
    query = "SELECT * FROM transfers"
    filters = []
    values = []

    if params:
        for k, v in params.items():
            filters.append(f"{k} = %s")
            values.append(v)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY block_number DESC"

    logger.info(f"Fetching transfers with params: {params}")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, values)
            return cur.fetchall()


# ----------------------------
# FETCH PROGRESS
# ----------------------------
def insert_fetch_progress(progress: FetchProgress):
    query = """
    INSERT INTO fetch_progress (
        network, chunk_start, chunk_end, log_count
    ) VALUES (
        %(network)s, %(chunk_start)s, %(chunk_end)s, %(log_count)s
    )
    ON CONFLICT (network, chunk_start, chunk_end) DO NOTHING;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, progress.to_dict())
            if cur.rowcount == 0:
                logger.warning(
                    f"Fetch progress already exists, skipped: network {progress.network}, "
                    f"chunk_start {progress.chunk_start}, chunk_end {progress.chunk_end}"
                )
            else:
                conn.commit()
                logger.debug(
                    f"Inserted fetch progress: network {progress.network}, "
                    f"chunk_start {progress.chunk_start}, chunk_end {progress.chunk_end}"
                )

def get_fetch_progress(params: dict = None) -> list[FetchProgress]:
    query = "SELECT network, chunk_start, chunk_end, log_count, completed_at FROM fetch_progress"
    filters = []
    values = []

    if params:
        for k, v in params.items():
            filters.append(f"{k} = %s")
            values.append(v)

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY chunk_start"

    logger.info(f"Fetching fetch progress with params: {params}")
    with get_connection() as conn:
        # Make sure you use RealDictCursor if you want dict-like rows
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, values)
            rows = cur.fetchall()

    progress_list = [
        FetchProgress(
            network=row['network'],
            chunk_start=row['chunk_start'],
            chunk_end=row['chunk_end'],
            log_count=row['log_count'],
            completed_at=row['completed_at']
        )
        for row in rows
    ]
    return progress_list

# ----------------------------
# Classify x402 agents
# ----------------------------
def update_x402_flags(network: Networks, addresses: set[str]):
    """
    Updates transfers table:
    - is_from_x402 = true if from_address in addresses
    - is_to_x402 = true if to_address in addresses
    """

    if not addresses:
        logger.warning("No x402 addresses provided, skipping update")
        return

    query = """
    UPDATE transfers
    SET
        is_from_x402 = (from_address = ANY(%s)),
        is_to_x402 = (to_address = ANY(%s))
    WHERE network = %s;
    """

    addr_list = list(addresses)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (addr_list, addr_list, network.name))
            conn.commit()

    logger.info(
        f"Updated x402 flags for {len(addresses)} agents on {network.name}"
    )

# ----------------------------
# Classify addresses
# ----------------------------

def update_event_flags(network, zero_address, logger: logging.Logger):
    """
    Updates transfers table:
    - event_class = 'MINT' if from_address is zero address
    - event_class = 'BURN' if to_address is zero address
    """

    query = """
    UPDATE transfers
    SET event_class = CASE
        WHEN from_address = %s THEN 'MINT'
        WHEN to_address = %s THEN 'BURN'
        ELSE event_class
    END
    WHERE network = %s
      AND event_class IS NULL;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (zero_address, zero_address, network.name))
            conn.commit()

    logger.info(f"Updated mint/burn event_class for {network.name}")
    
def update_cex_entity_flags(
    network,
    label: str,
    addresses: set[str],
    logger
):
    """.
    Updates transfers table:
    - from_entity_class += label if from_address in addresses
    - to_entity_class += label if to_address in addresses
    Only updates with CEX label
    """

    if not addresses:
        logger.warning(f"No {label} addresses provided, skipping update")
        return

    addr_list = list(addresses)

    query = """
            UPDATE transfers
            SET
                from_entity_class = CASE
                    WHEN from_address = ANY(%s)
                    THEN array(
                        SELECT DISTINCT unnest(
                            COALESCE(from_entity_class, ARRAY[]::text[])
                            || ARRAY[%s]
                        )
                    )
                    ELSE from_entity_class
                END,

                to_entity_class = CASE
                    WHEN to_address = ANY(%s)
                    THEN array(
                        SELECT DISTINCT unnest(
                            COALESCE(to_entity_class, ARRAY[]::text[])
                            || ARRAY[%s]
                        )
                    )
                    ELSE to_entity_class
                END
            WHERE network = %s
            AND (from_address = ANY(%s) OR to_address = ANY(%s));
            """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    addr_list,  # from match
                    label,      # from append
                    addr_list,  # to match
                    label,      # to append
                    network.name,
                    addr_list,
                    addr_list
                )
            )
            conn.commit()

    logger.info(f"Updated {label} flags for {network.name}")

def update_bridge_entity_flags(
    network: str,
    deposit_hashes: set[str],
    withdrawal_hashes: set[str],
    logger
):
    """
    Updates BRIDGE labels based on tx_hash:

    - deposit txs  → to_entity_class += BRIDGE
    - withdrawal txs → from_entity_class += BRIDGE
    """

    # --------------
    # SAFETY CHECK
    # --------------
    intersection = deposit_hashes & withdrawal_hashes
    if intersection:
        # if overlap, data corrupted, remove them
        deposit_hashes -= intersection
        withdrawal_hashes -= intersection

    deposit_list = list(deposit_hashes)
    withdrawal_list = list(withdrawal_hashes)

    if not deposit_list and not withdrawal_list:
        logger.warning(f"[{network}] No bridge tx hashes provided")
        return

    query = """
        UPDATE transfers
        SET
            to_entity_class = CASE
                WHEN tx_hash = ANY(%s)
                THEN array(
                    SELECT DISTINCT unnest(
                        COALESCE(to_entity_class, ARRAY[]::text[])
                        || ARRAY['BRIDGE']
                    )
                )
                ELSE to_entity_class
            END,

            from_entity_class = CASE
                WHEN tx_hash = ANY(%s)
                THEN array(
                    SELECT DISTINCT unnest(
                        COALESCE(from_entity_class, ARRAY[]::text[])
                        || ARRAY['BRIDGE']
                    )
                )
                ELSE from_entity_class
            END
        WHERE network = %s
        AND (tx_hash = ANY(%s) OR tx_hash = ANY(%s));
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    deposit_list,      # to_entity_class update
                    withdrawal_list,   # from_entity_class update
                    network,
                    deposit_list,
                    withdrawal_list
                )
            )
            conn.commit()

    logger.info(
        f"[{network}] BRIDGE tx classification updated | "
        f"deposit={len(deposit_list)} withdrawal={len(withdrawal_list)}"
    )



# ----------------------------
# GRAPH 
# ----------------------------

def upsert_pagerank_scores(network: str, token_symbol: str | None, ranks: dict):
    """
    Saves PageRank results into DB.
    """

    query = """
        INSERT INTO pagerank_scores (
            network,
            token_symbol,
            address,
            score
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (network, token_symbol, address)
        DO UPDATE SET
            score = EXCLUDED.score,
            computed_at = NOW();
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            for address, score in ranks.items():
                cur.execute(query, (
                    network,
                    token_symbol,
                    address,
                    float(score)
                ))

            conn.commit()
            

# ----------------------------
# UTILITIES
# ----------------------------
def get_latest_processed_block_from_db(network: Networks) -> int | None:
    """
    Returns the highest block_number processed for a given network
    from the transfers table.
    """
    query = """
    SELECT MAX(block_number) AS latest_block
    FROM transfers
    WHERE network = %s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (network.name,))
            row = cur.fetchone()

    if row and row["latest_block"] is not None:
        logger.info(f"Latest processed block in DB for {network}: {row['latest_block']:,}")
        return row["latest_block"]
    else:
        logger.error(f"No processed blocks found for network {network}")
        raise ValueError(f"No processed blocks found for network {network}")

def execute_sql_folder():
    """
    Executes all .sql files in the given folder in alphabetical order.
    """
    if not SQL_FOLDER_PATH.exists() or not SQL_FOLDER_PATH.is_dir():
        logger.error(f"SQL folder does not exist: {SQL_FOLDER_PATH}")
        return

    # Fetch all .sql files, sorted alphabetically
    sql_files = sorted(SQL_FOLDER_PATH.glob("*.sql"))
    if not sql_files:
        logger.warning(f"No .sql files found in folder: {SQL_FOLDER_PATH}")
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            for sql_file in sql_files:
                sql_content = sql_file.read_text()
                try:
                    cur.execute(sql_content)
                    conn.commit()
                    logger.info(f"Executed {sql_file.name} successfully")
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Error executing {sql_file.name}: {e}")
                    raise
                
def destroy_all_tables_and_indexes(schema: str = "public"):
    """
    Drops all tables and dependent indexes in the given schema.
    WARNING: This will permanently delete ALL data in the schema!
    """
    fetch_tables_sql = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = %s
      AND table_type = 'BASE TABLE';
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Fetch all tables in the schema
            cur.execute(fetch_tables_sql, (schema,))
            tables = [row["table_name"] for row in cur.fetchall()]

            if not tables:
                logger.info(f"No tables found in schema '{schema}'. Nothing to drop.")
                return

            # Drop all tables dynamically
            drop_sql = "DROP TABLE IF EXISTS " + ", ".join(f'"{t}"' for t in tables) + " CASCADE;"
            cur.execute(drop_sql)
            conn.commit()
            logger.warning(f"Dropped all tables and dependent indexes in schema '{schema}': {tables}")
                              
def reset_tables():
    """
    Deletes all data from tables and resets auto-increment IDs.
    WARNING: This will permanently delete all data in the tables!
    """
    query = """
    TRUNCATE TABLE
        transfers,
        fetch_progress
    RESTART IDENTITY CASCADE;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            conn.commit()
            logger.warning("All tables reset: transfers, fetch_progress")
            
if __name__ == "__main__":
    execute_sql_folder()