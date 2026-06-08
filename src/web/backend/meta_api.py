from fastapi import APIRouter
from src.enums import Networks, StableCoins

router = APIRouter(prefix="/meta")

@router.get("/networks")
def get_networks():
    return {
        "networks": [n.value.capitalize() for n in Networks]
    }
    
@router.get("/stablecoins")
def get_stablecoins():
    return {
        "stablecoins": [s.value.capitalize() for s in StableCoins]
    }

@router.get("/compatibility")
def get_compatibility():

    return {
        Networks.ETHEREUM.value: [
            StableCoins.USDT.value,
            StableCoins.USDC.value,
            StableCoins.DAI.value,
            StableCoins.XAUT.value
        ],
        Networks.POLYGON.value: [
            StableCoins.USDT.value,
            StableCoins.USDC.value,
            StableCoins.DAI.value
        ],
        Networks.OPTIMISM.value: [
            StableCoins.USDT.value,
            StableCoins.USDC.value,
            StableCoins.DAI.value
        ],
        Networks.ARBITRUM.value: [
            StableCoins.USDT.value,
            StableCoins.USDC.value,
            StableCoins.DAI.value
        ],
        Networks.AVALANCHE.value: [
            StableCoins.USDT.value,
            StableCoins.USDC.value,
            StableCoins.DAI.value
        ],
    }