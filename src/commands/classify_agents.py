import click
from enums import Networks
from helpers import get_logger
from classifiers.agent_classifier_client import classify_x402_agents, update_x402_agents_file

@click.command()
@click.option(
    '--network',
    type=click.Choice([network.name for network in Networks], case_sensitive=False),
    required=True,
    help='Blockchain network to fetch x402 agents from'
)
@click.option(
    '--update',
    is_flag=True,
    default=False,
    help='If set, saves x402 agents to file'
)
@click.pass_context
def classify_agents(ctx, network, update):
    """
    Fetch x402-supported agent contracts for a given network.

    Example:

      python3 src/cli.py classify_agents --network polygon

      python3 src/cli.py classify_agents --network ethereum 
    """

    logger = ctx.obj["logger"]

    network_enum = Networks[network.upper()]

    logger.info(f"Starting x402 agent classification for {network_enum.name}")

    if update:
        update_x402_agents_file(network_enum, logger)
        logger.info("Updated x402 agents and saved to file.")
  
    
    agents = classify_x402_agents(network_enum, logger)
    logger.info(f"Classified {len(agents)} x402 agents for {network_enum.name} from file.")
    
    logger.info("Done classifying x402 agents.")