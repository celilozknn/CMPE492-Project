import os, sys
import yaml
import json
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import *
from enums import *
    

def get_token_address(network: Networks, token: StableCoins) -> str:
    with open(CONFIG_FOLDER_PATH / "tokens.yaml", "r") as f:
        data = yaml.safe_load(f)
    return data[token.value]["contracts"][network.value]

def get_decimals(network: Networks, token: StableCoins) -> int:
    with open(CONFIG_FOLDER_PATH / "tokens.yaml", "r") as f:
        data = yaml.safe_load(f)
    return data[token.value]["decimals"]

def get_chain_id(network: Networks):
    with open(CONFIG_FOLDER_PATH / "networks.yaml", "r") as f:
        data = yaml.safe_load(f)
    return data[network.value]["chain_id"]

def hex_to_int(value, default=0):
    """Convert hex string to int, safely handling empty or invalid strings."""
    try:
        if value.startswith("0x") and len(value) > 2:
            return int(value, 16)
        else:
            return int(value)
    except:
        return default

def int_to_hex(value):
    """Convert int to hex string with 0x prefix."""
    return hex(value)
 
def is_erc20_transfer(log, should_debug):
    topics = log.get("topics", [])
    if len(topics) >= 3:
        return True
    
    if should_debug:
        with open(DEBUG_FOLDER_PATH / "skipped_log.json", "a") as f:
            f.write(json.dumps(log) + "\n")
    
    return False
     


def get_logger(name, level=logging.INFO):
    class ColoredFormatter(logging.Formatter):
        COLORS = {
            "DEBUG": "\033[36m",     # cyan
            "INFO": "\033[32m",      # green
            "WARNING": "\033[33m",   # yellow
            "ERROR": "\033[31m",     # red
            "CRITICAL": "\033[41m",  # red background
        }
        RESET = "\033[0m"

        def format(self, record):
            color = self.COLORS.get(record.levelname, self.RESET)
            record.levelname = f"{color}{record.levelname}{self.RESET}"
            record.msg = f"{color}{record.msg}{self.RESET}"
            return super().format(record)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.hasHandlers():
        handler = logging.StreamHandler()

        formatter = ColoredFormatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            "%Y-%m-%d %H:%M:%S"
        )

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

### INFURA HELPERS START ###
def get_infura_url():
    INFURA_API_KEY, _ = get_infura_key_and_secret()
    return f"https://mainnet.infura.io/v3/{INFURA_API_KEY}"

def get_infura_key_and_secret():
    INFURA_API_KEY = os.getenv("INFURA_API_KEY")
    INFURA_API_SECRET = os.getenv("INFURA_API_SECRET")
    return INFURA_API_KEY, INFURA_API_SECRET

def get_infura_auth():
    from requests.auth import HTTPBasicAuth
    
    INFURA_API_KEY, INFURA_API_SECRET = get_infura_key_and_secret()
    return HTTPBasicAuth(INFURA_API_KEY, INFURA_API_SECRET)

def get_infura_headers():
    return {
        'content-type': 'application/json',
    }

def validate_infura_api_credentials(logger):    
    INFURA_API_KEY, INFURA_API_SECRET = get_infura_key_and_secret()
    
    # Check if API key and secret are loaded
    if not INFURA_API_KEY:
        logger.error("INFURA_API_KEY not found in environment variables")
        raise ValueError("INFURA_API_KEY not found in environment variables")
    if not INFURA_API_SECRET:
        logger.error("INFURA_API_SECRET not found in environment variables")
        raise ValueError("INFURA_API_SECRET not found in environment variables")
### INFURA HELPERS END ###