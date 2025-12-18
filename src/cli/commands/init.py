import contextlib
from pathlib import Path
import webbrowser

from chalkbox import Alert, Spinner, Stepper, get_console
import click
import yaml

from src.cli.wizard import CANCEL_HINT, prompt_filters, prompt_source, prompt_target, run_oauth_flow
from src.config.config_loader import get_default_config_path
from src.config.models import SpotifyConfig
from src.spotify.auth import SpotifyAuthManager
from src.utils.logger import get_logger

logger = get_logger(__name__)
console = get_console()

STEPS = [
    "Spotify Developer App",
    "API Credentials",
    "Sync Group Configuration",
    "Target Playlist",
    "Filter Options",
]


@click.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output path for config file (default: auto-detected)",
)
@click.pass_context
def init(ctx: click.Context, output: str | None) -> None:
    """Interactive setup wizard for SpotiSync configuration."""
    try:
        console.print("[bold]Setup Wizard[/bold]")
        console.print(
            f"[dim]This wizard will guide you through SpotiSync configuration.[/dim] {CANCEL_HINT}"
        )
        console.print()

        stepper = Stepper.from_list(STEPS)

        stepper.start(0)
        console.print(stepper)
        console.print()
        console.print("[bold]You need a Spotify Developer App to use SpotiSync.[/bold]")
        console.print()

        has_app = click.confirm("Do you have a Spotify Developer App?", default=False)

        if not has_app:
            console.print()
            console.print("[cyan]Opening Spotify Developer Dashboard...[/cyan]")
            console.print(
                "[link=https://developer.spotify.com/dashboard]https://developer.spotify.com/dashboard[/link]"
            )
            with contextlib.suppress(Exception):
                webbrowser.open("https://developer.spotify.com/dashboard")

            console.print()
            console.print("[bold]To create an app:[/bold]")
            console.print("  [cyan]1.[/cyan] Click 'Create app'")
            console.print("  [cyan]2.[/cyan] Fill in app name and description")
            console.print(
                "  [cyan]3.[/cyan] Set Redirect URI to: [green]https://example.com/callback[/green]"
            )
            console.print("  [cyan]4.[/cyan] Click 'Save'")
            console.print()

            console.print("[bold]What would you like to do?[/bold]")
            console.print("  [cyan]1.[/cyan] Enter credentials")
            console.print("  [cyan]2.[/cyan] Cancel setup")
            console.print()

            next_action = click.prompt("Choose option", type=click.Choice(["1", "2"]), default="1")
            if next_action == "2":
                stepper.fail(0)
                console.print(stepper)
                console.print(Alert.warning("Setup cancelled"))
                raise click.Abort()

        stepper.complete(0)

        stepper.start(1)
        console.print()
        console.print(stepper)
        console.print()
        console.print("[bold]Enter your Spotify app credentials:[/bold]")
        console.print()

        client_id = click.prompt("Client ID", type=str).strip()
        client_secret = click.prompt("Client Secret", type=str, hide_input=True).strip()
        redirect_uri = click.prompt(
            "Redirect URI",
            type=str,
            default="https://example.com/callback",
        ).strip()

        console.print()
        console.print("[dim]Note: We use https://example.com/callback for manual auth[/dim]")
        console.print("[dim](No HTTPS server required - you'll paste the redirect URL)[/dim]")
        console.print()

        spotify_config = SpotifyConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=[
                "user-library-read",
                "playlist-read-private",
                "playlist-modify-public",
                "playlist-modify-private",
            ],
        )

        auth_manager = SpotifyAuthManager(spotify_config)

        try:
            spotify_client = run_oauth_flow(auth_manager, max_attempts=3)
            console.print(Alert.success("Authentication successful!"))
        except Exception as e:
            stepper.fail(1)
            console.print(stepper)
            console.print(Alert.error("Authentication failed after 3 attempts", details=str(e)))
            raise click.Abort() from None

        stepper.complete(1)

        stepper.start(2)
        console.print()
        console.print(stepper)
        console.print()

        sync_name = click.prompt(
            "Name for this sync (e.g., 'daily-liked-sync')",
            type=str,
            default="my-sync",
        ).strip()

        source = prompt_source(spotify_client)
        stepper.complete(2)

        stepper.start(3)
        console.print()
        console.print(stepper)

        target = prompt_target(spotify_client)
        stepper.complete(3)

        stepper.start(4)
        console.print()
        console.print(stepper)

        filters = prompt_filters()
        skip_podcasts = filters["skip_podcasts"]

        stepper.complete(4)

        config_dict = {
            "spotify": {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "scopes": [
                    "user-library-read",
                    "playlist-read-private",
                    "playlist-modify-public",
                    "playlist-modify-private",
                ],
            },
            "filters": {
                "skip_podcasts": skip_podcasts,
            },
            "cron": {
                "enabled": True,
                "schedule": "*/10 * * * *",
            },
            "sync_groups": [
                {
                    "name": sync_name,
                    "source": source,
                    "target": target,
                }
            ],
        }

        config_path = Path(output) if output else get_default_config_path()

        config_path.parent.mkdir(parents=True, exist_ok=True)

        with Spinner("Saving configuration") as spinner:
            with open(config_path, "w") as f:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
            spinner.success(f"Configuration saved to: {config_path}")

        console.print()
        console.print(stepper)
        console.print()

        console.print(Alert.success("Setup complete!", details="SpotiSync is ready to use"))
        console.print()

        console.print("[bold]Next steps:[/bold]")
        console.print("  [cyan]1.[/cyan] Test sync:    [bold]spotisync sync --dry-run[/bold]")
        console.print("  [cyan]2.[/cyan] Run sync:     [bold]spotisync sync[/bold]")
        console.print("  [cyan]3.[/cyan] Check status: [bold]spotisync status[/bold]")
        console.print()

        console.print("[dim]To add more sync groups, run: spotisync add[/dim]")
        console.print("[dim]Run 'spotisync --help' for more commands.[/dim]")
        console.print()

    except click.Abort:
        console.print()
        console.print("[dim]Cancelled.[/dim]")
        ctx.exit(1)
    except Exception as e:
        logger.error(f"Setup error: {e}")
        console.print(Alert.error("Setup failed", details=str(e)))
        ctx.exit(1)
