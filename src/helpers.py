import os, sys
import yaml
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import *


def get_token_address(network:str, token:str):
    with open(CONFIG_FOLDER_PATH / "tokens.yaml", "r") as f:
        data = yaml.safe_load(f)
    return data[token]["contracts"][network]

def get_chain_id(network:str):
    with open(CONFIG_FOLDER_PATH / "networks.yaml", "r") as f:
        data = yaml.safe_load(f)
    return data[network]["chain_id"]

def hex_to_int(value, default=0):
    """Convert hex string to int, safely handling empty or invalid strings."""
    try:
        if value.startswith("0x") and len(value) > 2:
            return int(value, 16)
        else:
            return int(value)
    except:
        return default
    
def is_erc20_transfer(log, should_debug):
    topics = log.get("topics", [])
    if len(topics) >= 3:
        return True
    
    if should_debug:
        with open(DEBUG_FOLDER_PATH / "skipped_log.json", "a") as f:
            f.write(json.dumps(log) + "\n")
    
    return False
     