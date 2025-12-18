from datetime import datetime

from chalkbox import Alert, Table, get_console
import click

from src.cli.wizard import CANCEL_HINT, run_oauth_flow
from src.config.config_loader import get_token_path, load_typed_config
from src.spotify.auth import SpotifyAuthManager
from src.utils.logger import get_logger

logger = get_logger(__name__)
console = get_console()


@click.command()
@click.option("--clear", is_flag=True, help="Clear existing authentication token")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
@click.pass_context
def auth(ctx: click.Context, clear: bool, yes: bool) -> None:
    """Authenticate with Spotify and save credentials."""
    try:
        config_file = ctx.obj.get("config_file")
        config = load_typed_config(config_path=config_file)

        auth_manager = SpotifyAuthManager(config.spotify)

        if clear:
            if auth_manager.is_authenticated():
                if not yes and not click.confirm("Clear authentication token?", default=False):
                    console.print("[dim]Cancelled.[/dim]")
                    return
                auth_manager.clear_token()
                console.print(Alert.success("Authentication token cleared"))
                console.print()

        elif auth_manager.is_authenticated():
            token_info = auth_manager.get_token_info()
            if token_info:
                expires_at = datetime.fromtimestamp(token_info.get("expires_at", 0))

                info_table = Table(headers=["Property", "Value"], title="Current Authentication")
                info_table.add_row("Status", "Authenticated", severity="success")
                info_table.add_row("Token expires", expires_at.strftime("%Y-%m-%d %H:%M:%S"))
                console.print()
                console.print(info_table)
                console.print()
                console.print("[dim]To re-authenticate, run: spotisync auth --clear[/dim]")
                return

        console.print()
        console.print("[bold cyan]Spotify Authentication[/bold cyan]")
        console.print(f"[dim]Connect SpotiSync to your Spotify account.[/dim] {CANCEL_HINT}")
        console.print()

        spotify_client = run_oauth_flow(auth_manager)
        user = spotify_client.get_current_user()
        token_info = auth_manager.get_token_info()
        expires_at = datetime.fromtimestamp(token_info.get("expires_at", 0) if token_info else 0)

        console.print()
        result_table = Table(headers=["Property", "Value"], title="Authentication Successful")
        result_table.add_row("User", user.get("display_name", "Unknown"))
        result_table.add_row("Spotify ID", user.get("id", "N/A"))
        result_table.add_row("Token stored", str(get_token_path()))
        result_table.add_row("Expires", expires_at.strftime("%Y-%m-%d %H:%M:%S"))
        console.print(result_table)
        console.print()

    except click.Abort:
        console.print()
        console.print("[dim]Cancelled.[/dim]")
        ctx.exit(1)
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        console.print(Alert.error("Authentication failed", details=str(e)))
        ctx.exit(1)
