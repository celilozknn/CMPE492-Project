import requests
import pandas as pd
import json
import dotenv
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import *

dotenv.load_dotenv()

SKIPPED_COUNTER = 0
SHOULD_DEBUG = True
SHOULD_SAVE_TO_CSV = True

# Your API key
API_KEY = os.getenv("ETHERSCAN_API_KEY")

# USDT contract
USDT_ADDRESS = "0xdAC17F958D2ee523a2206206994597C13D831ec7"

# Block range (adjust as needed)
FROM_BLOCK = 24585544
TO_BLOCK = 24585544
ETHERIUM_MAINNET_CHAIN_ID = 1

url = (
    f"https://api.etherscan.io/v2/api"
    f"?chainid={ETHERIUM_MAINNET_CHAIN_ID}"
    f"&apikey={API_KEY}"
    f"&module=logs"
    f"&action=getLogs"
    f"&address={USDT_ADDRESS}"
    f"&startblock={FROM_BLOCK}"
    f"&endblock={TO_BLOCK}"
)



def hex_to_int(value, default=0):
    """Convert hex string to int, safely handling empty or invalid strings."""
    try:
        if value.startswith("0x") and len(value) > 2:
            return int(value, 16)
        else:
            return int(value)
    except:
        return default
    
def is_erc20_transfer(log):
    topics = log.get("topics", [])
    if len(topics) >= 3:
        return True
    
    if SHOULD_DEBUG:
        with open(DEBUG_FOLDER_PATH / "skipped_log.json", "a") as f:
            f.write(json.dumps(log) + "\n")
    global SKIPPED_COUNTER
    SKIPPED_COUNTER += 1    
    print("Skipping log with insufficient topics:", log, "\nSkipped count:", SKIPPED_COUNTER)
    
    return False
        

def main():
    response = requests.get(url)

    try:
        data = response.json()
    except Exception as e:
        print("Failed to decode JSON:", e)
        print("Response text:", response.text)
        exit()

    # Check for errors
    if data.get("status") != "1":
        print("Error:", data.get("message"), data.get("result"))
        exit()

    logs = data["result"]

    # Save raw logs
    if SHOULD_DEBUG:
        with open(DEBUG_FOLDER_PATH / "raw_logs_pretty.json", "w") as f:
            json.dump(logs, f, indent=4)

    # Parse logs
    parsed_logs = []
    for log in logs:
        
        # Skip logs that don't have at least 3 topics (standard ERC-20 Transfer)
        if not is_erc20_transfer(log):
            continue

        address = log.get("address", "").lower()
        topics = log.get("topics", [])
        event_signature = topics[0]
        from_address = "0x" + topics[1][-40:]
        to_address = "0x" + topics[2][-40:]
        data_clean = hex_to_int(log["data"], 0)
        gas_price = hex_to_int(log.get("gasPrice", "0"), 0)
        gas_used = hex_to_int(log.get("gasUsed", "0"), 0)
        log_index = hex_to_int(log.get("logIndex", "0"), 0)
        transaction_hash = log.get("transactionHash", "")
        transaction_index = hex_to_int(log.get("transactionIndex", "0"), 0)
        
        parsed_logs.append({
            "address": address,
            "event_signature": event_signature,
            "from_address": from_address,
            "to_address": to_address,
            "value_raw": data_clean,
            "value_usdt": data_clean / 1e6,  # USDT has 6 decimals
            "blockNumber": int(log["blockNumber"], 16),
            "blockHash": log["blockHash"],
            "timestamp": int(log["timeStamp"], 16),
            "gas_price": gas_price,
            "gas_used": gas_used,
            "log_index": log_index,
            "transaction_hash": transaction_hash,
            "transaction_index": transaction_index,
            "raw_log": log
        })

    # Create DataFrame for easier analysis
    df = pd.DataFrame(parsed_logs)
    print(df.head(30))

    # Optionally save to CSV
    if SHOULD_SAVE_TO_CSV:
        df.to_csv(DEBUG_FOLDER_PATH / "usdt_logs.csv", index=False)
    
if __name__ == "__main__":
    main()