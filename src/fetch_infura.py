import requests
import pandas as pd
import time, os
import dotenv
import json

from collections import Counter
from datetime import datetime, timezone

from helpers import *
from paths import *
from enums import *

dotenv.load_dotenv()

"""
URLS:
https://mainnet.infura.io/v3/{INFURA_API_KEY}
https://polygon-mainnet.infura.io/v3/{INFURA_API_KEY}
https://optimism-mainnet.infura.io/v3/{INFURA_API_KEY}
https://arbitrum-mainnet.infura.io/v3/{INFURA_API_KEY}
https://avalanche-mainnet.infura.io/v3/{INFURA_API_KEY}
"""

def address_to_token_symbol_and_decimals(token_map: dict, address: str) -> tuple:
    info = token_map.get(address.lower(), {"symbol": "Unknown", "decimals": 18})
    return info["symbol"], info["decimals"]

def fetch_logs(url, from_block=None, to_block=None, address=None, topics=None, logger=None):
    """
    Fetch logs from Infura using eth_getLogs.
    Parameters:
        url (str): Infura endpoint URL.
        from_block (str): Hex string or tag (e.g., 'latest').
        to_block (str): Hex string or tag.
        address (str or list): Contract address or list of addresses.
        topics (list): List of topic strings.
    Returns:
        List of log objects or error dict.
    """    
    params = {}
    if from_block or to_block:
        if from_block:
            params['fromBlock'] = from_block
        if to_block:
            params['toBlock'] = to_block
    if address:
        params['address'] = address
    if topics:
        params['topics'] = topics

    logger.info(
        f"Fetching logs | fromBlock={hex_to_int(params.get('fromBlock')):,} "
        f"toBlock={hex_to_int(params.get('toBlock')):,} "
        f"number of addresses={len(params.get('address', []))} "
        f"topics={params.get('topics')}"
    )
    
    payload_logs = {
        "jsonrpc": "2.0",
        "method": "eth_getLogs",
        "params": [params],
        "id": 1
    }
    
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
        return resp_json['error']
    
    logs = resp_json.get('result', [])
    logger.info(f"Received {len(logs)} logs from RPC")
    if len(logs) > 9000:
        logger.warning("Log count close to 10k limit. Consider reducing block chunk size.")
    return logs

def decode_log(token_map: dict, log: dict) -> dict:
    address = log["address"].lower()
    token_symbol, token_decimals = address_to_token_symbol_and_decimals(token_map, address)
    
    return {
        "log_index": int(log["logIndex"], 16),
        "tx_index": int(log["transactionIndex"], 16),
        "tx_hash": log["transactionHash"],
        
        "block_hash": log["blockHash"],
        "block_number": int(log["blockNumber"], 16),
        "block_timestamp": int(log["blockTimestamp"], 16),

        "contract_address": address,
        "token_symbol": token_symbol,

        "topic": log["topics"][0],
        "from": ("0x" + log["topics"][1][-40:]).lower(),
        "to": ("0x" + log["topics"][2][-40:]).lower(),
        
        "raw_value": int(log["data"], 16),
        "value": int(log["data"], 16) / (10 ** token_decimals),

        "raw_log": log
    }

def main():
        
    ### CONFIGURE THE BLOCK RANGE ###
    start_block = int_to_hex(24608077)
    end_block = int_to_hex(24608077)
    #################################
    
    logger = get_logger("InfuraEventFetcher")

    INFURA_URL = get_infura_url()

    USDT_ADDRESS = get_token_address(network=Networks.ETHEREUM, token=StableCoins.USDT).lower()
    USDC_ADDRESS = get_token_address(network=Networks.ETHEREUM, token=StableCoins.USDC).lower()
    DAI_ADDRESS = get_token_address(network=Networks.ETHEREUM, token=StableCoins.DAI).lower()
    XAUT_ADDRESS = get_token_address(network=Networks.ETHEREUM, token=StableCoins.XAUT).lower()

    USDT_DECIMALS = get_decimals(network=Networks.ETHEREUM, token=StableCoins.USDT)
    USDC_DECIMALS = get_decimals(network=Networks.ETHEREUM, token=StableCoins.USDC)
    DAI_DECIMALS = get_decimals(network=Networks.ETHEREUM, token=StableCoins.DAI)
    XAUT_DECIMALS = get_decimals(network=Networks.ETHEREUM, token=StableCoins.XAUT)

    COIN_ADDRESSES = [USDT_ADDRESS, USDC_ADDRESS, DAI_ADDRESS, XAUT_ADDRESS]
        
    TOKEN_MAPPING = {
        USDT_ADDRESS: {"symbol": "USDT", "decimals": USDT_DECIMALS},
        USDC_ADDRESS: {"symbol": "USDC", "decimals": USDC_DECIMALS},
        DAI_ADDRESS: {"symbol": "DAI", "decimals": DAI_DECIMALS},
        XAUT_ADDRESS: {"symbol": "XAUT", "decimals": XAUT_DECIMALS},
    }

    TRANSFER_EVENT_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"  # keccak256("Transfer(address,address,uint256)")

    validate_infura_api_credentials(logger)
    
    logger.info(f"Using Infura URL: {INFURA_URL}")
    logger.info(f"Tracking contract addresses: {COIN_ADDRESSES}")
    logger.info(f"Tracking tokens: {list(TOKEN_MAPPING.values())}")
    logger.info(f"Starting log fetch for block range {hex_to_int(start_block):,} -> {hex_to_int(end_block):,}")
    
    logs = fetch_logs(
        url=INFURA_URL,
        from_block=start_block,
        to_block=end_block,
        address=COIN_ADDRESSES,
        topics=[TRANSFER_EVENT_TOPIC],
        logger=logger
    )
    
    now_utc = datetime.now(timezone.utc)
    ts = now_utc.strftime("%Y%m%d_%H%M%S") # gives UTC not Istanbul, "20260308_205135"
    output_file_path = OUTPUT_FOLDER_PATH / f"infura_logs_{ts}.json"

    with open(output_file_path, 'w') as f:
        logger.info(f"Decoding {len(logs)} logs")
        decoded_logs = [decode_log(TOKEN_MAPPING, log) for log in logs]
        json.dump(decoded_logs, f, indent=4)
    
    logger.info(f"Saved {len(decoded_logs)} decoded logs to {output_file_path}")
    
    token_counts = Counter([log["token_symbol"] for log in decoded_logs])
    logger.info(f"Token transfer summary: {dict(token_counts)}")
    
    logger.info("Run completed successfully")


if __name__ == "__main__":
    main()