import requests
import time
import json
import os

from helpers import get_chain_id
from enums import Networks
from dotenv import load_dotenv
import os

load_dotenv()

API_BASE = "https://8004scan.io/api/v1/public"

SLEEP_SECONDS = 7 # 10 req/min safe buffer

scan_8004_API_KEY = os.getenv("SCAN_API_KEY")


def load_x402_agents(network: Networks, limit: int = 5000) -> set[str]:
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

        print(
            f"[rate] limit={limit_hdr} "
            f"remaining={remaining_hdr} "
            f"reset={reset_hdr}"
        )

        resp = r.json()
        data = resp.get("data", [])

        # optional debug
        with open(f"x402_agents_{network.value}_page_{page}.json", "w") as f:
            json.dump(resp, f, indent=2)

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

        print(
            f"[page={page}] fetched={len(data)} "
            f"seen={total_seen} "
            f"x402={len(out)} "
            f"hasMore={has_more}"
        )

        if not has_more:
            break
        
        if page == 2:
            print("Reached page 2, stopping to avoid long runtimes during testing.")
            break

        page += 1
        time.sleep(SLEEP_SECONDS)

    return out


if __name__ == "__main__":
    network = Networks.POLYGON

    agents = load_x402_agents(network)

    with open(f"x402_agents_{network.value}.txt", "w") as f:
        for addr in sorted(agents):
            f.write(addr + "\n")

    print(f"Done. x402 agents: {len(agents)}")