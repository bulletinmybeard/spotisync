import json
import sys

from chalkbox import Alert, get_console
import click
import yaml

from src.config.config_loader import ConfigLoader

console = get_console()


@click.command()
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON (for piping to jq, etc.)",
)
@click.pass_context
def config(ctx: click.Context, output_json: bool) -> None:
    """Display current configuration."""
    try:
        config_file = ctx.obj.get("config_file")
        loader = ConfigLoader(config_path=config_file)
        config_dict = loader.load()

        if output_json:
            print(json.dumps(config_dict, indent=2))
        else:
            yaml_output = yaml.dump(config_dict, default_flow_style=False, sort_keys=False)
            console.print()
            console.print("[bold cyan]Current Configuration[/bold cyan]")
            console.print()
            console.print(f"[dim]{yaml_output}[/dim]")

    except Exception as e:
        if output_json:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        else:
            console.print(Alert.error("Failed to load configuration", details=str(e)))
            ctx.exit(1)
