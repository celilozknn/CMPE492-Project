import requests
import time
import json
import os
import logging
import yaml

from helpers import get_chain_id, get_logger, get_logger
from enums import Networks
from dotenv import load_dotenv
from paths import CONFIG_FOLDER_PATH, DEBUG_FOLDER_PATH

from db import update_x402_flags

load_dotenv()

API_BASE = "https://8004scan.io/api/v1/public"

SLEEP_SECONDS = 7 # 10 req/min safe buffer

scan_8004_API_KEY = os.getenv("SCAN_API_KEY")


def fetch_x402_agents(network: Networks, logger:logging.Logger, limit: int = 5000) -> set[str]:
    """
    Returns set of contract addresses that support x402 for a given network.
    Uses API key for higher rate limits.
    """

    if not scan_8004_API_KEY:
        raise ValueError("SCAN_API_KEY is not set")

    chain_id = get_chain_id(network)
    url = f"{API_BASE}/agents"

    session = requests.Session()

    headers = {
        "X-API-Key": scan_8004_API_KEY,
        "Accept": "application/json"
    }

    out: set[str] = set()

    page = 1
    total_seen = 0

    logger.info(f"Fetching x402 agents for {network.name}, will wait {SLEEP_SECONDS}s between requests to respect rate limits")
    
    while True:
        params = {
            "chainId": chain_id,
            "limit": limit,
            "page": page
        }

        r = session.get(url, params=params, headers=headers)
        r.raise_for_status()

        # ===== RATE LIMIT HEADERS =====
        limit_hdr = r.headers.get("X-RateLimit-Limit")
        remaining_hdr = r.headers.get("X-RateLimit-Remaining")
        reset_hdr = r.headers.get("X-RateLimit-Reset")

        logger.info(
            f"[rate] limit={limit_hdr} "
            f"remaining={remaining_hdr} "
            f"reset={reset_hdr}"
        )

        resp = r.json()
        data = resp.get("data", [])

        with open(DEBUG_FOLDER_PATH / f"x402_agents_{network.value}_page_{page}.json", "w") as f:
            json.dump(resp, f, indent=4)

        if not data:
            break

        for agent in data:
            total_seen += 1

            if agent.get("x402_supported") is True:
                addr = agent.get("owner_address").lower()
                if addr:
                    out.add(addr.lower())

        pagination = resp.get("meta", {}).get("pagination", {})
        has_more = pagination.get("hasMore", False)

        logger.info(
            f"[page={page}] fetched={len(data)} "
            f"total seen={total_seen} "
            f"total x402={len(out)} "
            f"hasMore={has_more}"
        )
    
        if not has_more:
            break
        

        page += 1
        time.sleep(SLEEP_SECONDS)

    logger.info(f"Finished fetching x402 agents for {network.name}. Total seen: {total_seen}, x402 supported: {len(out)}")
    return out

def save_x402_agents(network: Networks, agents: set[str], logger: logging.Logger):
    output_path = CONFIG_FOLDER_PATH / f"x402_agent_addresses_{network.value}.yaml"

    with open(output_path, "w") as f:
        f.write(f"{network.value.lower()}:\n")

        for addr in agents:
            f.write(f"  - {addr}\n")

    logger.info(f"Saved {len(agents)} x402 agent addresses for {network.name} to {output_path}")

def load_x402_agents(network: Networks, logger) -> set[str]:
    input_path = CONFIG_FOLDER_PATH / f"x402_agent_addresses_{network.value}.yaml"

    if not input_path.exists():
        logger.warning(f"No x402 agents file found for {network.name} at {input_path}")
        return set()

    with open(input_path, "r") as f:
        data = yaml.safe_load(f) or {}

    raw_list = data.get(network.value.lower(), [])

    agents = {str(addr).lower() for addr in raw_list}

    logger.info(
        f"Loaded {len(agents)} x402 agent addresses for {network.name} from {input_path}"
    )

    return agents

def classify_x402_agents(network: Networks, logger) -> set[str]:
    """
    Loads x402 agents and updates DB flags.
    """

    agent_addresses = load_x402_agents(network, logger)

    for addr in agent_addresses:
        logger.debug(f"Classified x402 agent: {addr}")
        
    logger.info(
        f"Obtained {len(agent_addresses)} x402 agents for {network.name}"
    )

    update_x402_flags(network, agent_addresses)

    logger.info(f"DB updated for x402 classification on {network.name}")

    return agent_addresses

def update_x402_agents_file(network: Networks, logger: logging.Logger):
    agents = fetch_x402_agents(network, logger)
    save_x402_agents(network, agents, logger)
    