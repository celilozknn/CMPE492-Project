

import requests
import pandas as pd
import time, os
import dotenv
import json

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

INFURA_URL = get_infura_url()

USDT_ADDRESS = get_token_address(network=Networks.ETHEREUM, token=StableCoins.USDT).lower()
USDC_ADDRESS = get_token_address(network=Networks.ETHEREUM, token=StableCoins.USDC).lower()
DAI_ADDRESS = get_token_address(network=Networks.ETHEREUM, token=StableCoins.DAI).lower()
XAUT_ADDRESS = get_token_address(network=Networks.ETHEREUM, token=StableCoins.XAUT).lower()
COIN_ADDRESSES = [USDT_ADDRESS, USDC_ADDRESS, DAI_ADDRESS, XAUT_ADDRESS]

TRANSFER_EVENT_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"  # keccak256("Transfer(address,address,uint256)")


def address_to_token_symbol(address: str) -> str:
    TOKEN_SYMBOL_BY_ADDRESS = {
        USDT_ADDRESS: "USDT",
        USDC_ADDRESS: "USDC",
        DAI_ADDRESS: "DAI",
        XAUT_ADDRESS: "XAUT",
    }
    
    return TOKEN_SYMBOL_BY_ADDRESS.get(address.lower(), "Unknown")
    
def fetch_logs(from_block=None, to_block=None, address=None, topics=None, logger=None):
    """
    Fetch logs from Infura using eth_getLogs.
    Parameters:
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

    logger.info(f"Fetching logs with params: {params.items()}")
    payload_logs = {
        "jsonrpc": "2.0",
        "method": "eth_getLogs",
        "params": [params],
        "id": 1
    }
    
    auth = get_infura_auth()
    headers = get_infura_headers()

    response = requests.post(
        INFURA_URL,
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
    return resp_json.get('result', [])

def decode_log(log: dict) -> dict:
    address = log["address"].lower()
    
    return {
        "log_index": int(log["logIndex"], 16),
        "tx_index": int(log["transactionIndex"], 16),
        "tx_hash": log["transactionHash"],
        
        "block_hash": log["blockHash"],
        "block_number": int(log["blockNumber"], 16),
        "block_timestamp": int(log["blockTimestamp"], 16),

        "contract_address": address,
        "token_symbol": address_to_token_symbol(address),

        "topic": log["topics"][0],
        "from": ("0x" + log["topics"][1][-40:]).lower(),
        "to": ("0x" + log["topics"][2][-40:]).lower(),
        
        "raw_value":  log["data"],
        "value": int(log["data"], 16),

        "raw_log": log
    }

def main():
    logger = get_logger("InfuraEventFetcher")

    validate_infura_api_credentials(logger)
    
    logger.info(f"Using Infura URL: {INFURA_URL}")

    logs = fetch_logs(
        from_block=int_to_hex(24608077),
        to_block=int_to_hex(24608077),
        address=COIN_ADDRESSES,
        topics=[TRANSFER_EVENT_TOPIC],
        logger=logger
    )
    
    with open(OUTPUT_FOLDER_PATH / "infura_logs.json", 'w') as f:
        json.dump([decode_log(log) for log in logs], f, indent=4)


if __name__ == "__main__":
    main()