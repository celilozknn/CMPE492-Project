import requests
import pandas as pd
import json
import os
import dotenv

from paths import *
from helpers import *

dotenv.load_dotenv()

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")

SHOULD_DEBUG = True
SHOULD_SAVE_TO_CSV = True


def fetch_events(network, chain_id, token, from_block, to_block):

    token_address = get_token_address(network=network, token=token)

    print(f"Fetching {token.upper()} from {network.upper()} network, address:", token_address, "\n")

    url = (
        f"https://api.etherscan.io/v2/api"
        f"?chainid={chain_id}"
        f"&apikey={ETHERSCAN_API_KEY}"
        f"&module=logs"
        f"&action=getLogs"
        f"&address={token_address}"
        f"&startblock={from_block}"
        f"&endblock={to_block}"
    )

    response = requests.get(url)
    data = response.json()

    if data.get("status") != "1":
        print("Error:", data.get("message"), data.get("result"))
        return None

    logs = data["result"]

    if SHOULD_DEBUG:
        with open(DEBUG_FOLDER_PATH / f"{token}_{network}_raw_logs.json", "w") as f:
            json.dump(logs, f, indent=4)

    parsed_logs = []

    for log in logs:

        if not is_erc20_transfer(log, SHOULD_DEBUG):
            continue

        topics = log["topics"]
        value_raw = hex_to_int(log["data"], 0)

        parsed_logs.append({
            "network": network,
            "token": token,
            "address": log["address"].lower(),
            "event_signature": topics[0],
            "from_address": "0x" + topics[1][-40:],
            "to_address": "0x" + topics[2][-40:],
            "value_raw": value_raw,
            "value_token": value_raw / 1e6,
            "blockNumber": int(log["blockNumber"], 16),
            "blockHash": log["blockHash"],
            "timestamp": int(log["timeStamp"], 16),
            "gas_price": hex_to_int(log.get("gasPrice", "0"), 0),
            "gas_used": hex_to_int(log.get("gasUsed", "0"), 0),
            "log_index": hex_to_int(log.get("logIndex", "0"), 0),
            "transaction_hash": log["transactionHash"],
            "transaction_index": hex_to_int(log.get("transactionIndex", "0"), 0),
            "raw_log": log
        })

    df = pd.DataFrame(parsed_logs)

    if SHOULD_SAVE_TO_CSV:
        df.to_csv(DEBUG_FOLDER_PATH / f"{token}_{network}_logs.csv", index=False)

    print(df.head(30))

    return df