from importlib.metadata import version

import click

from src.cli.commands.add import add
from src.cli.commands.auth import auth
from src.cli.commands.config import config
from src.cli.commands.init import init
from src.cli.commands.status import status
from src.cli.commands.sync import sync
from src.utils.logger import setup_logging


@click.group(invoke_without_command=True)
@click.option(
    "--config",
    "-c",
    "config_file",
    type=click.Path(exists=True),
    help="Path to config file (default: auto-detected)",
)
@click.version_option(version=version("spotisync"))
@click.pass_context
def cli(ctx: click.Context, config_file: str | None) -> None:
    ctx.ensure_object(dict)
    ctx.obj["config_file"] = config_file

    setup_logging()

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


cli.add_command(add)
cli.add_command(auth)
cli.add_command(config)
cli.add_command(init)
cli.add_command(status)
cli.add_command(sync)


if __name__ == "__main__":
    cli()
