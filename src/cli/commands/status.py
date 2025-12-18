from datetime import datetime
import json
import sys
from typing import Any

from chalkbox import Alert, Table, get_console
import click

from src.config.config_loader import ConfigValidationError, get_effective_filters, load_typed_config
from src.config.models import FiltersConfig
from src.spotify.auth import SpotifyAuthManager
from src.spotify.client import SpotifyClient
from src.sync.engine import SyncEngine
from src.utils.logger import get_logger

logger = get_logger(__name__)
console = get_console()


@click.command()
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON (for piping to jq, etc.)",
)
@click.pass_context
def status(ctx: click.Context, output_json: bool) -> None:
    """Show current configuration and authentication status."""
    try:
        config_file = ctx.obj.get("config_file")
        config = load_typed_config(config_path=config_file)

        auth_manager = SpotifyAuthManager(config.spotify)
        token_info = auth_manager.get_token_info()
        spotify_client = None

        status_data: dict[str, Any] = {
            "authentication": None,
            "sync_groups": [],
            "filters": {
                "skip_podcasts": config.filters.skip_podcasts,
                "exclude": {
                    "artists": config.filters.exclude.artists,
                    "albums": config.filters.exclude.albums,
                    "tracks": config.filters.exclude.tracks,
                },
            },
            "cron": {
                "enabled": config.cron.enabled,
                "schedule": config.cron.schedule if config.cron.enabled else None,
            },
        }

        if token_info:
            expires_at = datetime.fromtimestamp(token_info.get("expires_at", 0))
            now = datetime.now()
            time_until_expiry = expires_at - now

            try:
                spotify_client = SpotifyClient(auth_manager)
                user = spotify_client.get_current_user()
                user_name = user.get("display_name", "Unknown")
                user_id = user.get("id", "N/A")
            except Exception as e:
                logger.debug(f"Could not fetch user info: {e}")
                user_name = None
                user_id = None

            status_data["authentication"] = {
                "authenticated": True,
                "user": user_name,
                "spotify_id": user_id,
                "expires_at": expires_at.isoformat(),
                "seconds_remaining": max(0, int(time_until_expiry.total_seconds())),
                "refresh_token_available": True,
            }
        else:
            status_data["authentication"] = {"authenticated": False}

        for sync_group in config.sync_groups:
            group_data: dict[str, Any] = {
                "name": sync_group.name,
                "source": sync_group.source,
                "target": sync_group.target,
                "enabled": not sync_group.disabled,
            }

            if spotify_client and not sync_group.disabled:
                effective_filters = get_effective_filters(config, sync_group)
                sync_engine = SyncEngine(spotify_client, sync_group, effective_filters)
                try:
                    group_data["source_info"] = sync_engine.get_source_info()
                    group_data["target_info"] = sync_engine.get_target_info()
                except Exception as e:
                    logger.debug(f"Could not fetch source/target info for {sync_group.name}: {e}")

            status_data["sync_groups"].append(group_data)

        if output_json:
            print(json.dumps(status_data, indent=2))
            return

        console.print("\n[bold cyan]SpotiSync Status[/bold cyan]\n")

        if token_info:
            expires_at = datetime.fromtimestamp(token_info.get("expires_at", 0))
            now = datetime.now()
            time_until_expiry = expires_at - now

            auth_info = status_data["authentication"]
            auth_table = Table(headers=["Property", "Value"], title="Authentication")
            auth_table.add_row("Status", "Authenticated", severity="success")
            auth_table.add_row("User", auth_info.get("user") or "<error fetching>")
            auth_table.add_row("Spotify ID", auth_info.get("spotify_id") or "N/A")
            auth_table.add_row("Token Expires", expires_at.strftime("%Y-%m-%d %H:%M:%S"))

            if time_until_expiry.total_seconds() > 0:
                total_seconds = int(time_until_expiry.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60

                time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes} minutes"

                if total_seconds < 3600:
                    auth_table.add_row("Time Remaining", time_str, severity="warning")
                else:
                    auth_table.add_row("Time Remaining", time_str, severity="info")

                auth_table.add_row(
                    "Refresh Token", "Available (auto-refresh enabled)", severity="success"
                )
            else:
                auth_table.add_row(
                    "Time Remaining",
                    "Expired (will auto-refresh)",
                    severity="warning",
                )
                auth_table.add_row("Refresh Token", "Available", severity="info")

            console.print(auth_table)

        else:
            console.print(
                Alert.warning("Not authenticated", details="Run 'spotisync auth' to authenticate")
            )

        sync_groups_table = Table(
            headers=["Name", "Source", "Target", "Status"],
            title=f"Sync Groups ({len(config.sync_groups)})",
        )

        for sync_group in config.sync_groups:
            source_display = (
                "Liked Tracks"
                if sync_group.source == "liked_tracks"
                else sync_group.source[:12] + "..."
            )
            target_display = sync_group.target[:12] + "..."
            status_str = "Disabled" if sync_group.disabled else "Enabled"
            severity = "orphaned" if sync_group.disabled else "success"

            sync_groups_table.add_row(
                sync_group.name, source_display, target_display, status_str, severity=severity
            )

        console.print(sync_groups_table)

        if spotify_client:
            for sync_group in config.sync_groups:
                if sync_group.disabled:
                    continue

                console.print(f"\n[bold]{sync_group.name}[/bold]")

                effective_filters = get_effective_filters(config, sync_group)
                sync_engine = SyncEngine(spotify_client, sync_group, effective_filters)

                try:
                    source_info = sync_engine.get_source_info()
                    target_info = sync_engine.get_target_info()

                    detail_table = Table(headers=["Property", "Value"], title="Details")
                    detail_table.add_row("Source Type", source_info.get("type", "Unknown"))
                    if "name" in source_info:
                        detail_table.add_row("Source Name", source_info["name"])
                    if "total_tracks" in source_info:
                        detail_table.add_row("Source Tracks", str(source_info["total_tracks"]))

                    detail_table.add_row("Target Name", target_info.get("name", "Unknown"))
                    detail_table.add_row("Target Tracks", str(target_info.get("total_tracks", 0)))
                    public_str = "Yes" if target_info.get("public") == "Yes" else "No"
                    detail_table.add_row("Public", public_str)

                    console.print(detail_table)

                except Exception as e:
                    logger.debug(f"Could not fetch details for {sync_group.name}: {e}")
                    console.print(Alert.warning(f"Could not fetch details for {sync_group.name}"))

        _display_filters(config.filters, "Root Filters (Defaults)")

        cron_table = Table(headers=["Setting", "Value"], title="Root Cron Configuration")
        cron_table.add_row("Enabled", str(config.cron.enabled))
        if config.cron.enabled:
            cron_table.add_row("Schedule", config.cron.schedule)
        console.print(cron_table)

        console.print()

    except ConfigValidationError as e:
        if output_json:
            print(json.dumps({"error": f"Configuration validation failed: {e}"}), file=sys.stderr)
            sys.exit(1)
        console.print(Alert.error("Configuration validation failed", details=e.formatted_message()))
        ctx.exit(1)
    except Exception as e:
        if output_json:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        logger.error(f"Status error: {e}")
        console.print(Alert.error("Status command failed", details=str(e)))
        ctx.exit(1)


def _display_filters(filters: FiltersConfig, title: str) -> None:
    filter_table = Table(headers=["Filter", "Value"], title=title)
    filter_table.add_row("Skip Podcasts", str(filters.skip_podcasts))

    exclude = filters.exclude
    if exclude.artists:
        filter_table.add_row("Exclude Artists", str(len(exclude.artists)))
    if exclude.albums:
        filter_table.add_row("Exclude Albums", str(len(exclude.albums)))
    if exclude.tracks:
        filter_table.add_row("Exclude Tracks", str(len(exclude.tracks)))

    console.print(filter_table)
