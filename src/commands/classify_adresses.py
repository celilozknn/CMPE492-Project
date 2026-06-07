import click
from enums import Networks
from classifiers.address_classifier_client import classify_addresses

@click.command()
@click.option(
    '--network',
    type=click.Choice([network.name for network in Networks], case_sensitive=False),
    required=True,
    help='Blockchain network to classify addresses for'
)
@click.pass_context
def classify_addresses_cmd(ctx, network, update):
    """
    Classify addresses as CEX, DEX, Bridge, Mint, Burn, etc.

    Example:

      python3 src/cli.py classify_addresses --network polygon
      python3 src/cli.py classify_addresses --network ethereum 
    """

    logger = ctx.obj["logger"]

    network_enum = Networks[network.upper()]

    logger.info(f"Starting address classification for {network_enum.name}")

    classify_addresses(network_enum, logger)

    logger.info(f"Done address classification for {network_enum.name}")
    logger.info("Done address classification.")