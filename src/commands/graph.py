import click
from enums import Networks
from helpers import get_logger

from graph.graph_service import run_pagerank_graph


@click.command()
@click.option(
    '--network',
    type=click.Choice([n.name for n in Networks], case_sensitive=False),
    required=True,
    help='Blockchain network'
)
@click.option(
    '--token',
    type=str,
    required=False,
    help='Token symbol filter (USDT, USDC, DAI, XAUT)'
)
@click.option(
    '--top',
    type=int,
    default=20,
    help='Top N results to display'
)
@click.option(
    '--save/--no-save',
    default=True,
    help='Save PageRank results to database'
)
@click.pass_context
def graph(ctx, network, token, top, save):
    """
    Build transaction graph and compute PageRank.

    Example:
      python3 src/cli.py graph --network ethereum
    """

    logger = ctx.obj["logger"]
    network_enum = Networks[network.upper()]

    logger.info(f"Starting graph analysis | {network_enum.name} | token={token}")

    run_pagerank_graph(
        network=network_enum,
        token_symbol=token,
        top_n=top,
        logger=logger,
        save=save
    )

    logger.info("Graph analysis completed")