
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class StableCoins(Enum):
    USDT = "USDT"
    USDC = "USDC"
    DAI = "DAI"
    XAUT = "XAUT"
    
class Networks(Enum):
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    OPTIMISM = "optimism"
    ARBITRUM = "arbitrum"
    AVALANCHE = "avalanche"

@dataclass
class FetchProgress:
    network: str
    chunk_start: int
    chunk_end: int
    log_count: int
    completed_at: datetime = None

    def to_dict(self):
        return {
            "network": self.network,
            "chunk_start": self.chunk_start,
            "chunk_end": self.chunk_end,
            "log_count": self.log_count,
        }
    
# TODO: add Transfer class, better than using a dict.