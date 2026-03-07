
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