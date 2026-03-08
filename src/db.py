import sys, os
import psycopg2
from psycopg2.extras import RealDictCursor
import dotenv

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
    logger.info(f"Inserting transfer: {transfer['tx_hash']} log_index: {transfer['log_index']} "
                 f"network: {transfer['network']}")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, transfer)
            if cur.rowcount == 0:
                logger.warning(f"Transfer already exists, skipped: {transfer['tx_hash']}")
            else:
                conn.commit()
                logger.info(f"Inserted transfer: {transfer['tx_hash']}")


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
                logger.info(
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
    
if __name__ == "__main__":
    transfer_data = {
        "log_index": 12,
        "tx_index": 1,
        "tx_hash": "0x0c317b940c94ee2d4e2ab309f515db3d1292dbf47cad309ee747db6f37fe1539",
        "block_hash": "0xb557b6e76da0afb08e85f455e0aa5c8ea9ecdea3e24982822bdea1789b6e7b4f",
        "block_number": 148669200,
        "block_timestamp": None,
        "network": "OPTIMISM",
        "token_symbol": "USDC",
        "token_address": "0x0b2c639c533813f4aa9d7837caf62653d097ff85",
        "topic": "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
        "from_address": "0x478946bcd4a5a22b316470f5486fafb928c0ba25",  # mapped from "from"
        "to_address": "0x63f8d4000ba6fe867dcb581eaa20a1bc89dcc15e",   # mapped from "to"
        "raw_value": 149768370538,
        "value": 149768.370538
    }

    #insert_transfer(transfer_data)
    
    #print(get_transfers({"network": "OPTIMISM", "token_symbol": "USDC"}))

    insert_fetch_progress(FetchProgress(network=Networks.ETHEREUM.name, chunk_start=1200, chunk_end=1600, log_count=70))

    progresses = get_fetch_progress({"network": Networks.ETHEREUM.name})
    for p in progresses:
        print(p)