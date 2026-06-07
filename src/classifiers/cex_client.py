import os
import time
import requests
import logging
import yaml
import json

from collections import Counter
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import Set

from enums import Networks
from helpers import get_chain_id, get_logger
from db import update_entity_flags
from paths import CONFIG_FOLDER_PATH, DEBUG_FOLDER_PATH

load_dotenv()

DUNE_API_KEY = os.getenv("DUNE_API_KEY")

ETHEREUM_QUERY_ID = "7673004"
ARBITRUM_QUERY_ID = "7672881"
POLYGON_QUERY_ID = "7673006"
AVALANCHE_QUERY_ID = "7673012"
OPTIMISM_QUERY_ID = "7673008"


QUERY_ID_MAP = {
    Networks.ETHEREUM: ETHEREUM_QUERY_ID,
    Networks.ARBITRUM: ARBITRUM_QUERY_ID,
    Networks.POLYGON: POLYGON_QUERY_ID,
    Networks.AVALANCHE: AVALANCHE_QUERY_ID,
    Networks.OPTIMISM: OPTIMISM_QUERY_ID
}

DUNE_BASE = "https://api.dune.com/api/v1/query"


def fetch_cex_addresses_from_dune(network: Networks, logger: logging.Logger) -> Set[str]:
    headers = {
        "X-Dune-API-Key": DUNE_API_KEY
    }

    payload = {
        "query_parameters": {
            "blockchain": network.value.lower()
        }
    }
    
    query_id = QUERY_ID_MAP.get(network)
    if not query_id:
        logger.error(f"No Dune query ID configured for {network.name}")
        return set()
    
    url = f"{DUNE_BASE}/{query_id}/results"

    all_addresses: Set[str] = set()

    while url:
        r = requests.get(url, headers=headers, json=payload)
        logger.info(
            f"Fetching CEX addresses from Dune: {url}"
        )
        
        logger.info(f"Request payload: {payload}")
        r.raise_for_status()

        data = r.json()

        with open(DEBUG_FOLDER_PATH / f"dune_cex_addresses_{int(time.time())}.json", "w") as f:
            json.dump(data, f, indent=4)
            
        # extract rows safely
        rows = data.get("result", {}).get("rows", [])

        for row in rows:
            addr = row.get("address")
            if addr:
                all_addresses.add(addr.lower())

        logger.info(
            f"Fetched batch: {len(rows)} rows | total={len(all_addresses)}"
        )

        # required for next page - if no next_uri, loop will end
        url = data.get("next_uri")

        # small sleep to be safe with rate limits
        time.sleep(0.2)

    logger.info(f"Finished fetching CEX wallets: {len(all_addresses)} total")

    return all_addresses

def save_cex_addresses(network: Networks, items: set[str], logger: logging.Logger):
    output_path = CONFIG_FOLDER_PATH / f"cex_addresses_{network.value}.yaml"

    addresses = list(items)

    with open(output_path, "w") as f:
        f.write(f"{network.value.lower()}:\n")

        for addr in addresses:
            f.write(f"  - \"{addr}\"\n")

    logger.info(f"Saved {len(addresses)} CEX addresses -> {output_path}")
    
def load_cex_addresses(network: Networks, logger: logging.Logger) -> list[dict]:
    input_path = CONFIG_FOLDER_PATH / f"cex_addresses_{network.value}.yaml"

    if not input_path.exists():
        logger.warning(f"No CEX file found for {network.name}")
        return []

    with open(input_path, "r") as f:
        data = yaml.safe_load(f) or {}

    return data.get(network.value.lower(), [])

def update_cex_addresses_file(network: Networks, logger: logging.Logger):
    cex_addresses = fetch_cex_addresses_from_dune(network, logger)
    save_cex_addresses(network, cex_addresses, logger)

def classify_cex_addresses(network: Networks, update: bool, logger: logging.Logger):
    if update:
        update_cex_addresses_file(network, logger)
        
    cex_addresses = load_cex_addresses(network, logger)

    update_entity_flags(network, "CEX", cex_addresses, logger)

    logger.info("DB updated for CEX classification")

    return cex_addresses