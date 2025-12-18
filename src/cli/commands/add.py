from typing import Any

from chalkbox import Alert, Spinner, Stepper, get_console
import click
import yaml

from src.cli.wizard import CANCEL_HINT, prompt_sync_group
from src.config.config_loader import (
    ConfigValidationError,
    get_default_config_path,
    load_typed_config,
)
from src.spotify.auth import SpotifyAuthManager
from src.spotify.client import SpotifyClient
from src.utils.logger import get_logger

logger = get_logger(__name__)
console = get_console()

STEPS = [
    "Sync Group Configuration",
    "Target Playlist",
    "Filter Options",
]


@click.command()
@click.pass_context
def add(ctx: click.Context) -> None:
    """Add a new sync group to existing configuration."""
    try:
        config_file = ctx.obj.get("config_file")
        config_path = config_file if config_file else get_default_config_path()

        with Spinner("Loading configuration") as spinner:
            config = load_typed_config(config_path=config_file)
            spinner.success(f"Loaded config from: {config_path}")

        auth_manager = SpotifyAuthManager(config.spotify)
        if not auth_manager.is_authenticated():
            console.print(Alert.warning("Not authenticated", details="Please run: spotisync auth"))
            raise click.Abort()

        spotify_client = SpotifyClient(auth_manager)

        existing_names = [g.name for g in config.sync_groups]

        console.print()
        console.print("[bold cyan]Add Sync Group[/bold cyan]")
        console.print(f"[dim]Add a new sync group to your configuration.[/dim] {CANCEL_HINT}")
        console.print()

        stepper = Stepper.from_list(STEPS)

        stepper.start(0)
        console.print(stepper)
        console.print()

        sync_group = prompt_sync_group(
            spotify_client,
            existing_names=existing_names,
            prompt_for_filters=False,
        )

        stepper.complete(0)
        stepper.complete(1)

        stepper.start(2)
        console.print()
        console.print(stepper)

        use_custom_filters = click.confirm(
            "\nConfigure custom filters for this sync group?",
            default=False,
        )

        filters_dict = None
        if use_custom_filters:
            console.print()
            console.print("[bold]Configure track filtering:[/bold]")
            console.print()

            skip_podcasts = click.confirm("Skip podcasts?", default=True)

            filters_dict = {
                "skip_podcasts": skip_podcasts,
            }

        stepper.complete(2)

        new_sync_group: dict[str, Any] = {
            "name": sync_group.name,
            "source": sync_group.source,
            "target": sync_group.target,
        }
        if filters_dict:
            new_sync_group["filters"] = filters_dict

        with open(config_path, encoding="utf-8") as f:
            raw_config = yaml.safe_load(f) or {}

        if "sync_groups" not in raw_config:
            raw_config["sync_groups"] = []
        raw_config["sync_groups"].append(new_sync_group)

        with Spinner("Saving configuration") as spinner:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(raw_config, f, default_flow_style=False, sort_keys=False)
            spinner.success(f"Configuration saved to: {config_path}")

        console.print()
        console.print(stepper)
        console.print()

        console.print(
            Alert.success(
                f"Sync group '{sync_group.name}' added!",
                details=f"Total sync groups: {len(raw_config['sync_groups'])}",
            )
        )
        console.print()

        console.print("[bold]Next steps:[/bold]")
        console.print(
            f"  [cyan]1.[/cyan] Test sync:    [bold]spotisync sync -n {sync_group.name} --dry-run[/bold]"
        )
        console.print(
            f"  [cyan]2.[/cyan] Run sync:     [bold]spotisync sync -n {sync_group.name}[/bold]"
        )
        console.print("  [cyan]3.[/cyan] Check status: [bold]spotisync status[/bold]")
        console.print()

    except click.Abort:
        console.print()
        console.print("[dim]Cancelled.[/dim]")
        ctx.exit(1)
    except ConfigValidationError as e:
        console.print(Alert.error("Configuration validation failed", details=e.formatted_message()))
        ctx.exit(1)
    except Exception as e:
        logger.error(f"Add sync group error: {e}")
        console.print(Alert.error("Failed to add sync group", details=str(e)))
        ctx.exit(1)
