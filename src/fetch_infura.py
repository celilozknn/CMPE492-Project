import requests
import pandas as pd
import time, os
import dotenv
import re
import json

from collections import Counter
from datetime import datetime, timezone

from helpers import *
from paths import *
from enums import *
from db import *

dotenv.load_dotenv()

def get_latest_block(network: Networks, logger):
    """
    Fetch the latest block number from the RPC endpoint.
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_blockNumber",
        "params": [],
        "id": 1
    }

    auth = get_infura_auth()
    headers = get_infura_headers()

    response = requests.post(
        url=get_infura_url(network=network),
        data=json.dumps(payload),
        headers=headers,
        auth=auth
    )

    resp_json = response.json()

    if "error" in resp_json:
        raise Exception(resp_json["error"]["message"])

    latest_block_hex = resp_json["result"]
    latest_block_int = int(latest_block_hex, 16)

    logger.info(f"Latest block: {latest_block_int:,}")

    return latest_block_int

def fetch_logs(url, network, from_block_int, to_block_int, default_chunk_size, token_address, topics, token_map, output_folder, logger):
    chunk_size = default_chunk_size
    chunk_from_block_int = from_block_int
    all_logs = []

    while chunk_from_block_int <= to_block_int:
        chunk_to_block_int = min(chunk_from_block_int + chunk_size - 1, to_block_int)
        chunk_range = f"{chunk_from_block_int}-{chunk_to_block_int}"
        
        logger.info(f"Fetching logs for block range {chunk_from_block_int:,} -> {chunk_to_block_int:,} (chunk size: {chunk_size})")
        
        try:
            logs = fetch_chunked_logs(
                url=url,
                from_block_hex=int_to_hex(chunk_from_block_int),
                to_block_hex=int_to_hex(chunk_to_block_int),
                token_address=token_address,
                topics=topics,
                logger=logger
            )
            
            all_logs.extend(logs)
            
            progress = FetchProgress(
                network=network,
                chunk_start=chunk_from_block_int,
                chunk_end=chunk_to_block_int,
                log_count=len(logs)
            )
            insert_fetch_progress(progress)
            
            logger.info(f"✓ Chunk {chunk_range}: {len(logs)} logs written")
            chunk_size = default_chunk_size 
            
            chunk_from_block_int = chunk_to_block_int + 1
            time.sleep(0.2)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error fetching chunk range {chunk_range}: {error_msg}")
            
            if "query returned more than 10000 results" in error_msg:
                try:
                    match = re.search(r'\[0x([0-9a-fA-F]+),\s*0x([0-9a-fA-F]+)\]', error_msg) # Parse Infura's suggested range
                    if match:
                        suggested_start = int(match.group(1), 16)
                        suggested_end = int(match.group(2), 16)
                        suggested_size = suggested_end - suggested_start + 1
                        logger.info(f"Infura suggests: {suggested_start} to {suggested_end} ({suggested_size} blocks)")
                        chunk_size = suggested_size
                        
                        # Check for impossible case (single block >10k logs)
                        if chunk_from_block_int == suggested_start and chunk_to_block_int == suggested_end:
                            logger.error(f"Range {chunk_range} has >10k logs! Skipping.")
                            chunk_from_block_int = chunk_to_block_int + 1
                            chunk_size = chunk_from_block_int  
                    else:
                        chunk_size = max(chunk_size // 10, 1)
                except Exception:
                    chunk_size = max(chunk_size // 10, 1)
            else:
                chunk_size = max(chunk_size // 2, 1)
            
            continue
    
    logger.info(f"Completed fetching {len(all_logs)} logs for block range {from_block_int:,} -> {to_block_int:,}")

    return all_logs

def fetch_chunked_logs(url, from_block_hex, to_block_hex, token_address, topics, logger):
    """
    Fetch logs from Infura using eth_getLogs.
    Parameters:
        url (str): Infura endpoint URL.
        from_block_hex (str): Hex string or tag (e.g., 'latest').
        to_block_hex (str): Hex string or tag.
        token_address (str or list): Token address or list of token addresses.
        topics (list): List of topic strings.
    Returns:
        List of log objects or error dict.
    """    
    params = {}
    if from_block_hex or to_block_hex:
        if from_block_hex:
            params['fromBlock'] = from_block_hex    
        if to_block_hex:
            params['toBlock'] = to_block_hex
    if token_address:
        params['address'] = token_address
    if topics:
        params['topics'] = topics

    logger.info(
        f"Fetching logs | fromBlock={hex_to_int(params.get('fromBlock')):,} "
        f"toBlock={hex_to_int(params.get('toBlock')):,} "
        f"number of token addresses={len(params.get('address', []))} "
        f"token addresses={params.get('address')} "
        f"topics={params.get('topics')}"
    )
    
    payload_logs = {
        "jsonrpc": "2.0",
        "method": "eth_getLogs",
        "params": [params],
        "id": 1
    }
    
    logger.debug(f"Payload for eth_getLogs: {json.dumps(payload_logs, indent=4)}")
    
    auth = get_infura_auth()
    headers = get_infura_headers()

    response = requests.post(
        url,
        data=json.dumps(payload_logs),
        headers=headers,
        auth=auth
    )
    
    logger.info(f"[eth_getLogs] Status: {response.status_code}")
    
    try:
        resp_json = response.json()
    except Exception as e:
        logger.error(f"Failed to decode JSON: {e}")
        logger.error(response.text)
        return None
    if 'error' in resp_json:
        logger.error(f"Error: {resp_json['error']}")
        raise Exception(resp_json['error']['message'])
    
    logs = resp_json.get('result', [])
    logger.info(f"Received {len(logs)} logs from RPC")
        
    return logs

def decode_log(token_map: dict, network: str, log: dict, logger: logging.Logger) -> dict:
    
    try: 
        token_address = log["address"].lower()
        token_symbol, token_decimals = token_address_to_token_symbol_and_decimals(token_map, token_address)
        
        if log.get("data") == "0x":
            if len(log.get("topics", [])) > 3:
                data = log["topics"][3]
                logger.warning(f"Using topic[3] as fallback for log: {log}")
            else:
                data = "0x0"
                logger.warning(f"Log has empty data and no topic[3], defaulting value to 0: {log}")
        else:
            data = log["data"]
            
        decoded =  {
            "log_index": int(log["logIndex"], 16),
            "tx_index": int(log["transactionIndex"], 16),
            "tx_hash": log["transactionHash"],
            
            "block_hash": log["blockHash"],
            "block_number": int(log["blockNumber"], 16),
            "block_timestamp": int(log["blockTimestamp"], 16) if "blockTimestamp" in log else None,

            "network": network,
            "token_symbol": token_symbol,
            "token_address": token_address,

            "topic": log["topics"][0],
            "from": ("0x" + log["topics"][1][-40:]).lower(),
            "to": ("0x" + log["topics"][2][-40:]).lower(),
            
            "raw_value": int(data, 16),
            "value": int(data, 16) / (10 ** token_decimals),

            "raw_log": log
        }
            
        return decoded
    except Exception as e:
        logger.error(f"Error decoding log: {e}")
        logger.error(f"Log data: {log}")
        

def main():
    start_time = time.time()
    logger = get_logger("InfuraEventFetcher")     
    
    ### CONFIGURE THE NETWORK ###
    NETWORK = Networks.ETHEREUM
    #################################

    start_block = get_latest_processed_block_from_db(network=NETWORK) + 1
    end_block = get_latest_block(network=NETWORK, logger=logger)
    
    INFURA_URL = get_infura_url(network=NETWORK)

    # Base tokens
    TOKENS = [
        StableCoins.USDT,
        StableCoins.USDC,
        StableCoins.DAI,
    ]

    # Network specific tokens
    if NETWORK == Networks.ETHEREUM:
        TOKENS.append(StableCoins.XAUT)

    TOKEN_MAPPING = {}

    for token in TOKENS:
        address = get_token_address(network=NETWORK, token=token).lower()
        decimals = get_decimals(network=NETWORK, token=token)

        TOKEN_MAPPING[address] = {
            "symbol": token.name,
            "decimals": decimals
        }

    TOKEN_ADDRESSES = list(TOKEN_MAPPING.keys())

    TRANSFER_EVENT_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

    validate_infura_api_credentials(logger)
    
    logger.info(f"Using Infura URL: {INFURA_URL}")
    logger.info(f"Tracking token addresses: {TOKEN_ADDRESSES}")
    logger.info(f"Tracking tokens: {[TOKEN_MAPPING[addr]['symbol'] for addr in TOKEN_ADDRESSES]}")
    logger.info(f"Starting log fetch for block range {start_block:,} -> {end_block:,}")
    
    fetched_logs = fetch_logs(
        url=INFURA_URL,
        network=NETWORK.name,
        from_block_int=start_block,
        to_block_int=end_block,
        default_chunk_size=40, 
        token_address=TOKEN_ADDRESSES,
        topics=[TRANSFER_EVENT_TOPIC],
        token_map=TOKEN_MAPPING,
        output_folder=OUTPUT_FOLDER_PATH,
        logger=logger
    )
    
    now_utc = datetime.now(timezone.utc)
    ts = now_utc.strftime("%Y%m%d_%H%M%S") # gives UTC not Istanbul, "20260308_205135"
    output_file_path = OUTPUT_FOLDER_PATH / f"infura_logs_{ts}.json"

    fetched_logs = [decode_log(token_map=TOKEN_MAPPING, network=NETWORK.name, log=log, logger=logger) for log in fetched_logs]
    
    token_counts = Counter()
    
    log_count = len(fetched_logs)
    batch_size = 10000
    
    for batch in range(0, log_count, batch_size):
        batch_logs = fetched_logs[batch:batch+batch_size]
        
        insert_transfers_batch(batch_logs)
    
        token_counts.update(log["token_symbol"] for log in batch_logs)
        
        batch_name = f"batch_{batch//batch_size + 1}"
        batch_file_path = OUTPUT_FOLDER_PATH / f"infura_logs_{ts}_{batch_name}.json"
        
        with open(batch_file_path, 'w') as f:
            json.dump(batch_logs, f, indent=4)
            
        logger.info(f"Saved batch of {len(batch_logs)} decoded logs to {batch_file_path}")
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.info(f"Token transfer summary: {dict(token_counts)}")
    logger.info(f"Run completed successfully in {elapsed_time:.2f} seconds. {start_time} - {end_time}. Total logs fetched: {log_count}.")

if __name__ == "__main__":
    main()