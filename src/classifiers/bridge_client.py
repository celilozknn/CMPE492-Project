import os
import time
import requests
import logging
import yaml
import json

from dotenv import load_dotenv

from enums import Networks
from db import update_bridge_entity_flags
from paths import CONFIG_FOLDER_PATH, DEBUG_FOLDER_PATH

load_dotenv()

DUNE_API_KEY = os.getenv("DUNE_API_KEY")

DUNE_BASE = "https://api.dune.com/api/v1/query"

BRIDGE_DEPOSIT_QUERY_IDS = {
    Networks.ETHEREUM: "7673021",
    Networks.ARBITRUM: "7673252",
    Networks.POLYGON: "7673301",
    Networks.AVALANCHE: "7673237", 
    Networks.OPTIMISM: "7673254",
}

BRIDGE_WITHDRAWAL_QUERY_IDS = {
    Networks.ETHEREUM: "7673360",
    Networks.ARBITRUM: "7673349", 
    Networks.POLYGON: "7673304", 
    Networks.AVALANCHE: "7673354", 
    Networks.OPTIMISM: "7673352",
}


def fetch_bridge_hashes_from_dune(
    query_id: str,
    logger: logging.Logger
) -> set[str]:

    headers = {
        "X-Dune-API-Key": DUNE_API_KEY
    }

    url = f"{DUNE_BASE}/{query_id}/results"

    hashes: set[str] = set()

    while url:
        logger.info(f"Fetching bridge hashes: {url}")

        r = requests.get(url, headers=headers)
        r.raise_for_status()

        data = r.json()

        rows = data.get("result", {}).get("rows", [])

        for row in rows:
            tx_hash = row.get("tx_hash")

            if tx_hash:
                hashes.add(tx_hash.lower())

        logger.info(
            f"Fetched batch: {len(rows)} rows | total={len(hashes)}"
        )

        url = data.get("next_uri")

        time.sleep(0.2)

    return hashes

def save_bridge_hashes(
    network: Networks,
    hashes: set[str],
    file_prefix: str,
    logger: logging.Logger
):
    path = CONFIG_FOLDER_PATH / f"{file_prefix}_{network.value}.yaml"

    with open(path, "w") as f:
        f.write(f"{network.value.lower()}:\n")

        for tx_hash in sorted(hashes):
            f.write(f"  - \"{tx_hash}\"\n")

    logger.info(
        f"Saved {len(hashes)} hashes -> {path}"
    )
    
def load_bridge_hashes(network: Networks, file_prefix: str, logger: logging.Logger) -> set[str]:

    path = CONFIG_FOLDER_PATH / f"{file_prefix}_{network.value}.yaml"

    if not path.exists():
        logger.warning(f"Missing file: {path}")
        return set()

    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    values = data.get(network.value.lower(), [])

    return {v.lower() for v in values if v}

def update_bridge_files(logger: logging.Logger):

    logger.info("Updating bridge yaml files")

    for network in Networks:

        deposit_query_id = BRIDGE_DEPOSIT_QUERY_IDS[network]
        withdrawal_query_id = BRIDGE_WITHDRAWAL_QUERY_IDS[network]

        deposits = fetch_bridge_hashes_from_dune(
            deposit_query_id,
            logger
        )

        withdrawals = fetch_bridge_hashes_from_dune(
            withdrawal_query_id,
            logger
        )

        save_bridge_hashes(
            network,
            deposits,
            "bridge_deposits",
            logger
        )

        save_bridge_hashes(
            network,
            withdrawals,
            "bridge_withdrawals",
            logger
        )

    logger.info("Bridge yaml update completed")

def classify_bridge_addresses(
    network: Networks,
    update: bool,
    logger: logging.Logger
):
    if update:
        update_bridge_files(logger)

    deposit_hashes = load_bridge_hashes(
        network,
        "bridge_deposits",
        logger
    )

    withdrawal_hashes = load_bridge_hashes(
        network,
        "bridge_withdrawals",
        logger
    )
    
    logger.info(
        f"Loaded {len(deposit_hashes)} deposit hashes and {len(withdrawal_hashes)} withdrawal hashes for {network.name}"
    )
    
    update_bridge_entity_flags(
        network.name.upper(),
        deposit_hashes,
        withdrawal_hashes,
        logger
    )

    update_bridge_entity_flags(
        network.name.upper(),
        deposit_hashes,
        withdrawal_hashes,
        logger
    )

    logger.info(
        f"DB updated for BRIDGE classification ({network.name})"
    )

    return {
        "deposits": deposit_hashes,
        "withdrawals": withdrawal_hashes
    }