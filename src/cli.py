import click
from helpers import get_logger
from commands.fetch import fetch
from commands.classify_agents import classify_agents
from commands.classify_adresses import classify_addresses
# from commands.graph import graph  # future
            
@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """
    Blockchain Stablecoin Flow Analysis Pipeline
    """
    ctx.ensure_object(dict)
    ctx.obj["logger"] = get_logger("CLI")

    if ctx.invoked_subcommand is None:
        click.echo("\nBlockchain Stablecoin Flow Analysis Pipeline\n")
        click.echo("Available commands:\n")
        commands = [
            ("fetch", "Fetch transfer logs from blockchain"),
            ("classify_agents", "Classify given transfer logs with x402 agent classifier"),
            ("classify_addresses", "Classify addresses (CEX, DEX, etc.)"),
            ("graph", "Generate network graphs [coming soon]"),
        ]
        max_len = max(len(cmd[0]) for cmd in commands)
        for cmd, desc in commands:
            click.echo(f"  {cmd.ljust(max_len)}  - {desc}")
        click.echo("\nUse 'python cli.py <command> --help' for command details.\n")

cli.add_command(fetch)
cli.add_command(classify_agents)
cli.add_command(classify_addresses)
# cli.add_command(graph)  # future

if __name__ == '__main__':
    cli()