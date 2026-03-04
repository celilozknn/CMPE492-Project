import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from event_fetcher import fetch_events
from helpers import get_chain_id

def main():
    NETWORK = "polygon"
    
    fetch_events(
        network=NETWORK,
        chain_id=get_chain_id(NETWORK),
        token="USDT",
        from_block=83769950,
        to_block=83769995
    )

if __name__ == "__main__":
    main()