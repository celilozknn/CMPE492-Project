import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from event_fetcher import fetch_events
from helpers import get_chain_id

def main():
    NETWORK = "ethereum"
    
    fetch_events(
        network=NETWORK,
        chain_id=get_chain_id(NETWORK),
        token="USDT",
        from_block=24585544,
        to_block=24585544
    )

if __name__ == "__main__":
    main()