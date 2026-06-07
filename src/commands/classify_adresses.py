import click
from enums import Networks
from helpers import get_logger
from classifiers.adress_classifier_client import classify_address_labels 


@click.command()
@click.option(
    '--network',
    type=click.Choice([network.name for network in Networks], case_sensitive=False),
    required=True,
    help='Blockchain network to fetch x402 agents from'
)
@click.pass_context
def classify_addresses(ctx, network):
    """
    Classify addresses (CEX, DEX, etc.) for a network.
    Example:

      python3 src/cli.py classify_addresses --network polygon

      python3 src/cli.py classify_addresses --network ethereum 
    """
    
    logger = ctx.obj["logger"]
    
    network_enum = Networks[network.upper()]

    logger.info(f"Starting address classification for {network_enum.name}")

    classify_address_labels(network_enum, logger)

    logger.info("Done address classification.")