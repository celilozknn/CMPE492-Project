import click
from commands.fetch import fetch
# from commands.classify import classify  # future
# from commands.graph import graph  # future

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """
    Blockchain Stablecoin Flow Analysis Pipeline
    """
    if ctx.invoked_subcommand is None:
        click.echo("\nBlockchain Stablecoin Flow Analysis Pipeline\n")
        click.echo("Available commands:\n")
        commands = [
            ("fetch", "Fetch transfer logs from blockchain"),
            ("classify", "Classify transfers (CEX, DEX, etc.) [coming soon]"),
            ("graph", "Generate network graphs [coming soon]"),
            ("status", "Show pipeline status [coming soon]")
        ]
        max_len = max(len(cmd[0]) for cmd in commands)
        for cmd, desc in commands:
            click.echo(f"  {cmd.ljust(max_len)}  - {desc}")
        click.echo("\nUse 'python cli.py <command> --help' for command details.\n")

cli.add_command(fetch)
# cli.add_command(classify)  # future
# cli.add_command(graph)  # future

if __name__ == '__main__':
    cli()