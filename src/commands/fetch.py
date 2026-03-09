import click
from enums import Networks
from helpers import get_logger
from db import get_latest_processed_block_from_db
from fetcher_client import run_fetcher, get_latest_block

logger = get_logger("CLI")

# We have 10k log limit for each response from Infura
# Hence I try to send block range that would likely contain around 10k logs. 
# We dont send a huge number since it consumes token but doesn't give logs 
# when there are more than 10k logs in the range. 
# So we try to find a sweet spot for each network based on current tx density.
NETWORK_REQUEST_STEP = {
    Networks.ETHEREUM: 40,      
    Networks.POLYGON: 10_000,    
    Networks.ARBITRUM: 20_000,    
    Networks.AVALANCHE: 25_000,   
    Networks.OPTIMISM: 125_000,    
}

@click.command()
@click.option(
    '--network',
    type=click.Choice([network.name for network in Networks], case_sensitive=False),
    required=True,
    help='Blockchain network to fetch from'
)
@click.option(
    '--auto/--manual',
    required=True,
    help='Auto Mode: fetches from the latest processed block in the DB to the latest chain block. '
         'Manual Mode: user specifies start/end blocks.'
)
@click.option(
    '--start',
    type=int,
    help='Start block (required if --manual)'
)
@click.option(
    '--end',
    type=int,
    help='End block (required if --manual)'
)
@click.pass_context
def fetch(ctx, network, auto, start, end):
    """
    Fetch ERC-20 transfer logs from blockchain.

Examples:

  # Auto mode:
    python3 src/cli.py fetch --network ethereum --auto

  # Manual mode:
    python3 src/cli.py fetch --network polygon --manual --start 50_000_000 --end 50_001_000
    (Block numbers for 2026.10.03 - ETHEREUM: 24622559, ARBITRUM: 440103332, POLYGON: 83985618, AVALANCHE: 79981230, OPTIMISM: 148746274)
    """

    network_enum = Networks[network.upper()]

    # Determine blocks
    if auto:
        start_block = get_latest_processed_block_from_db(network=network_enum) + 1
        end_block = get_latest_block(network=network_enum, logger=logger)
        logger.info(f"Auto mode: Fetching from {start_block:,} to {end_block:,}")
    else:
        if start is None or end is None:
            click.echo("Error: --start and --end are required in manual mode")
            raise click.UsageError("--start and --end are required in manual mode")
        start_block = start
        end_block = end
        logger.info(f"Manual mode: Fetching from {start_block:,} to {end_block:,}")

    if start_block > end_block:
        raise click.BadParameter(f"Start block ({start_block}) > end block ({end_block})")

    # Use hardcoded request step per network
    request_step = NETWORK_REQUEST_STEP.get(network_enum)
    logger.info(f"Network: {network_enum.name}, request step per RPC call: {request_step:,} blocks")

    run_fetcher(
        network=network_enum,
        start_block=start_block,
        end_block=end_block,
        request_step=request_step
    )

    logger.info("✓ Fetch completed")