import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers import get_chain_id
from event_fetcher import fetch_events


def main():
    NETWORK = "arbitrum"
    
    fetch_events(
        network=NETWORK,
        chain_id=get_chain_id(NETWORK),
        token="USDT",
        from_block=438361600,
        to_block=438361663
    )


if __name__ == "__main__":
    main()