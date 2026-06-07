import logging
from enums import Networks
from classifiers.cex_client import classify_cex_addresses

from db import update_event_flags


def classify_mint_burn(network: Networks, logger: logging.Logger) -> None:
    """
    CLI-facing orchestrator for mint/burn classification.
    Delegates actual DB update to DB layer.
    """

    logger.info(f"Starting mint/burn classification for {network.name}")
    ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
    
    update_event_flags(network, ZERO_ADDRESS, logger)

    logger.info(f"Completed mint/burn classification for {network.name}")
    
    


def classify_address_labels(network: Networks, update: bool, logger: logging.Logger) -> None:
    """
    CLI-facing orchestrator for address classification.
    Delegates actual classification logic to classifiers layer.
    """

    # Update mint/burn flags first since they are a specific type of address classification
    #classify_mint_burn(network, logger)
    #logger.info("Successfully classified mint/burn addresses.")
    
    # Cex classification
    classify_cex_addresses(network, update, logger)

    logger.info(f"Done address classification for {network.name}")