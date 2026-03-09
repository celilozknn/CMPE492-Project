import sys, os
import psycopg2
import dotenv
from psycopg2.extras import RealDictCursor, execute_values 

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import *
from helpers import *
from enums import *

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

# TODO: number of skipped is broken, although inserted says they are not.
def insert_transfers_batch(transfers: list[dict], batch_size: int):
    if not transfers:
        return

    query = """
    INSERT INTO transfers (
        log_index, tx_index, tx_hash, block_hash, block_number,
        block_timestamp, network, token_symbol, token_address,
        topic, from_address, to_address, raw_value, value
    ) VALUES %s
    ON CONFLICT (tx_hash, log_index, network) DO NOTHING
    RETURNING tx_hash;
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
                execute_values(cur, query, [to_tuple(t) for t in batch])
                
                inserted_rows = cur.fetchall()
                inserted = len(inserted_rows)
                skipped = len(batch) - inserted
                        
                conn.commit()
                if skipped > 0:
                    logger.warning(f"Batch insert: {inserted} inserted, {skipped} skipped due to conflict.")
                else:
                    logger.info(f"Batch size: {len(batch)} | Inserted: {inserted} | Skipped due to conflict: {skipped}")            
                
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