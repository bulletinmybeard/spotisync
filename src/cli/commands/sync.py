import json
import signal
import sys
from types import FrameType
from typing import Any

from chalkbox import Alert, Spinner, Table, get_console
import click

from src.config.config_loader import ConfigValidationError, get_effective_filters, load_typed_config
from src.config.models import SyncGroupConfig
from src.spotify.auth import SpotifyAuthManager
from src.spotify.client import SpotifyClient
from src.spotify.models import SpotifyTrack
from src.sync.diff import SyncDiff
from src.sync.engine import SyncEngine
from src.utils.logger import get_logger

logger = get_logger(__name__)
console = get_console()

_shutdown_requested = False
_json_mode = False


def _setup_graceful_shutdown() -> None:
    def signal_handler(signum: int, _frame: FrameType | None) -> None:
        global _shutdown_requested

        if _shutdown_requested:
            logger.warning("Force shutdown - terminating immediately")
            sys.exit(1)

        _shutdown_requested = True
        signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        logger.debug(f"Received {signal_name} - initiating graceful shutdown")
        if not _json_mode:
            console.print("\n[dim]Shutdown requested - completing current operation...[/dim]")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def is_shutdown_requested() -> bool:
    return _shutdown_requested


@click.command()
@click.option(
    "--dry-run",
    "-d",
    is_flag=True,
    help="Preview changes without applying them",
)
@click.option(
    "--name",
    "-n",
    multiple=True,
    help="Sync only specific sync group(s) by name (can be repeated)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON (for piping to jq, etc.)",
)
@click.pass_context
def sync(ctx: click.Context, dry_run: bool, name: tuple[str, ...], output_json: bool) -> None:
    """Sync source tracks to target playlist(s)."""
    global _json_mode
    _json_mode = output_json

    _setup_graceful_shutdown()

    try:
        config_file = ctx.obj.get("config_file")
        config = load_typed_config(config_path=config_file)

        auth_manager = SpotifyAuthManager(config.spotify)
        if not auth_manager.is_authenticated():
            if output_json:
                print(json.dumps({"error": "Not authenticated. Run: spotisync auth"}))
                sys.exit(1)
            console.print(Alert.warning("Not authenticated", details="Please run: spotisync auth"))
            raise click.Abort()

        spotify_client = SpotifyClient(auth_manager)

        sync_groups_to_run = config.get_enabled_sync_groups()

        if name:
            name_set = set(name)
            found = [g for g in sync_groups_to_run if g.name in name_set]
            missing = name_set - {g.name for g in found}

            if missing and not output_json:
                console.print(
                    Alert.warning(
                        "Unknown sync group(s)",
                        details=f"Not found: {', '.join(sorted(missing))}",
                    )
                )

            if not found:
                if output_json:
                    print(
                        json.dumps(
                            {"error": "No valid sync groups to process", "missing": list(missing)}
                        )
                    )
                    sys.exit(1)
                console.print(Alert.error("No valid sync groups to process"))
                raise click.Abort()

            sync_groups_to_run = found

        if not sync_groups_to_run:
            if output_json:
                print(json.dumps({"error": "No sync groups to run"}))
                sys.exit(1)
            console.print(
                Alert.warning(
                    "No sync groups to run",
                    details="All sync groups are disabled or no matching names found",
                )
            )
            return

        if not output_json:
            console.print(
                f"\n[bold cyan]SpotiSync - {len(sync_groups_to_run)} sync group(s)[/bold cyan]\n"
            )

        results: list[tuple[SyncGroupConfig, SyncDiff | None, str | None]] = []
        json_results: list[dict[str, Any]] = []

        for sync_group in sync_groups_to_run:
            if not output_json:
                console.print(f"\n[bold]Sync: {sync_group.name}[/bold]")
                console.print("-" * 50)

            try:
                # Check target playlist ownership to avoid wasting API calls
                is_owner, playlist_name, owner_id = spotify_client.validate_playlist_ownership(
                    sync_group.target
                )
                if not is_owner:
                    warning_msg = (
                        f"Target playlist '{playlist_name}' is not owned by you (owner: {owner_id})"
                    )
                    if output_json:
                        json_results.append(
                            {
                                "name": sync_group.name,
                                "status": "skipped",
                                "reason": warning_msg,
                            }
                        )
                    else:
                        console.print(
                            Alert.warning(f"Skipping: {sync_group.name}", details=warning_msg)
                        )
                    results.append((sync_group, None, None))
                    continue

                effective_filters = get_effective_filters(config, sync_group)
                sync_engine = SyncEngine(spotify_client, sync_group, effective_filters)

                if not output_json:
                    _display_sync_config(sync_engine)

                if output_json:
                    diff = sync_engine.run_sync(dry_run=dry_run)
                elif dry_run:
                    with Spinner(f"Analyzing changes for {sync_group.name}") as spinner:
                        diff = sync_engine.run_sync(dry_run=True)
                        spinner.success("Analysis complete!")
                else:
                    with Spinner(f"Syncing {sync_group.name}") as spinner:
                        diff = sync_engine.run_sync(dry_run=False)
                        spinner.success("Sync complete!")

                if not output_json:
                    _display_sync_results(diff, dry_run, sync_group)

                results.append((sync_group, diff, None))
                json_result: dict[str, Any] = {
                    "name": sync_group.name,
                    "status": "success",
                    "dry_run": dry_run,
                    "additions": len(diff.additions),
                    "unchanged": len(diff.unchanged),
                }
                if sync_group.skip_removals:
                    json_result["skipped_removals"] = len(diff.removals)
                else:
                    json_result["removals"] = len(diff.removals)
                json_results.append(json_result)

            except Exception as e:
                logger.error(f"Error syncing {sync_group.name}: {e}")
                if not output_json:
                    console.print(Alert.error(f"Failed: {sync_group.name}", details=str(e)))
                results.append((sync_group, None, str(e)))
                json_results.append(
                    {
                        "name": sync_group.name,
                        "status": "error",
                        "error": str(e),
                    }
                )

        if output_json:
            total_added = sum(
                r.get("additions", 0) for r in json_results if r["status"] == "success"
            )
            total_removed = sum(
                r.get("removals", 0) for r in json_results if r["status"] == "success"
            )
            total_skipped_removals = sum(
                r.get("skipped_removals", 0) for r in json_results if r["status"] == "success"
            )
            failed = sum(1 for r in json_results if r["status"] == "error")
            skipped = sum(1 for r in json_results if r["status"] == "skipped")

            summary: dict[str, Any] = {
                "total_groups": len(json_results),
                "successful": len(json_results) - failed - skipped,
                "failed": failed,
                "skipped": skipped,
                "total_additions": total_added,
            }
            if total_removed > 0:
                summary["total_removals"] = total_removed
            if total_skipped_removals > 0:
                summary["total_skipped_removals"] = total_skipped_removals

            print(
                json.dumps(
                    {
                        "dry_run": dry_run,
                        "sync_groups": json_results,
                        "summary": summary,
                    },
                    indent=2,
                )
            )
        else:
            _display_summary(results, dry_run)

    except click.Abort:
        raise
    except ConfigValidationError as e:
        if output_json:
            print(json.dumps({"error": f"Configuration validation failed: {e}"}), file=sys.stderr)
            sys.exit(1)
        console.print(Alert.error("Configuration validation failed", details=e.formatted_message()))
        raise click.Abort() from None
    except Exception as e:
        if output_json:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        logger.error(f"Sync error: {e}")
        console.print(Alert.error("Sync failed", details=str(e)))
        raise click.Abort() from None


def _display_sync_config(sync_engine: SyncEngine) -> None:
    source_info = sync_engine.get_source_info()
    target_info = sync_engine.get_target_info()

    config_table = Table(headers=["Property", "Value"], title="Configuration")
    config_table.add_row("Source", source_info.get("name", source_info.get("type", "Unknown")))
    if "total_tracks" in source_info:
        config_table.add_row("Source Tracks", str(source_info["total_tracks"]))
    config_table.add_row("Target", target_info.get("name", "Unknown"))
    config_table.add_row("Target Tracks", str(target_info.get("total_tracks", 0)))

    console.print(config_table)

    filters = sync_engine.filter_engine.get_filter_summary()
    active_filters = []
    if filters["skip_local_files"]:
        active_filters.append(("Skip local files", "Yes"))
    if filters["skip_podcasts"]:
        active_filters.append(("Skip podcasts", "Yes"))
    if filters["include_artists"]:
        active_filters.append(("Include artists", str(filters["include_artists"])))
    if filters["include_tracks"]:
        active_filters.append(("Include tracks", str(filters["include_tracks"])))
    if filters["exclude_artists"]:
        active_filters.append(("Exclude artists", str(filters["exclude_artists"])))
    if filters["exclude_albums"]:
        active_filters.append(("Exclude albums", str(filters["exclude_albums"])))
    if filters["exclude_tracks"]:
        active_filters.append(("Exclude tracks", str(filters["exclude_tracks"])))

    if active_filters:
        filter_table = Table(headers=["Filter", "Value"], title="Active Filters")
        for filter_name, filter_value in active_filters:
            filter_table.add_row(filter_name, filter_value)
        console.print(filter_table)


def _display_skipped_tracks(tracks: list[SpotifyTrack]) -> None:
    console.print("\n[dim]Target-only tracks (kept):[/dim]")
    for track in tracks[:10]:
        console.print(f"  [dim]~ {track.name} - {track.artist_names}[/dim]")
    if len(tracks) > 10:
        console.print(f"  [dim]... and {len(tracks) - 10} more[/dim]")


def _display_sync_results(diff: SyncDiff, dry_run: bool, sync_group: SyncGroupConfig) -> None:
    console.print()
    name = sync_group.name
    skip_removals = sync_group.skip_removals

    if dry_run:
        if len(diff.additions) > 0 or len(diff.removals) > 0:
            results_table = Table(headers=["Operation", "Count"], title="Planned Changes")
            if len(diff.additions) > 0:
                results_table.add_row("Would add", str(len(diff.additions)), severity="success")
            if len(diff.removals) > 0:
                if skip_removals:
                    results_table.add_row("Skipped", str(len(diff.removals)), severity="warning")
                else:
                    results_table.add_row("Would remove", str(len(diff.removals)), severity="info")
            console.print(results_table)

            if skip_removals and len(diff.removals) > 0:
                _display_skipped_tracks(diff.removals)
        else:
            console.print(Alert.success(f"{name}: No changes needed"))
    else:
        if len(diff.additions) > 0 or len(diff.removals) > 0:
            results_table = Table(headers=["Operation", "Count"], title="Changes Applied")
            if len(diff.additions) > 0:
                results_table.add_row("Added", str(len(diff.additions)), severity="success")
            if len(diff.removals) > 0:
                if skip_removals:
                    results_table.add_row("Skipped", str(len(diff.removals)), severity="warning")
                else:
                    results_table.add_row("Removed", str(len(diff.removals)), severity="info")
            results_table.add_row("Unchanged", str(len(diff.unchanged)), severity="orphaned")
            console.print(results_table)

            if skip_removals and len(diff.removals) > 0:
                _display_skipped_tracks(diff.removals)
        else:
            console.print(Alert.success(f"{name}: Already in sync"))


def _display_summary(
    results: list[tuple[SyncGroupConfig, SyncDiff | None, str | None]],
    dry_run: bool,
) -> None:
    if len(results) <= 1:
        return

    console.print("\n" + "=" * 60)
    console.print("[bold cyan]Summary[/bold cyan]\n")

    summary_table = Table(
        headers=["Sync Group", "Status", "Added", "Removed/Skipped"],
        title="Sync Results" if not dry_run else "Dry Run Results",
    )

    total_added = 0
    total_removed = 0
    total_skipped_removals = 0
    failed = 0
    skipped_groups = 0

    for sync_group, diff, error in results:
        if error:
            summary_table.add_row(sync_group.name, "Failed", "-", "-", severity="error")
            failed += 1
        elif diff is None and error is None:
            summary_table.add_row(sync_group.name, "Skipped", "-", "-", severity="warning")
            skipped_groups += 1
        elif diff:
            added = len(diff.additions)
            removal_count = len(diff.removals)
            total_added += added

            if sync_group.skip_removals:
                total_skipped_removals += removal_count
                removed_display = f"{removal_count} (skipped)" if removal_count > 0 else "0"
            else:
                total_removed += removal_count
                removed_display = str(removal_count)

            status = "OK" if added == 0 and removal_count == 0 else "Changed"
            severity = "success" if added == 0 and removal_count == 0 else "info"
            summary_table.add_row(
                sync_group.name, status, str(added), removed_display, severity=severity
            )

    console.print(summary_table)

    if failed > 0 or skipped_groups > 0:
        warning_parts = []
        if failed > 0:
            warning_parts.append(f"{failed} failed")
        if skipped_groups > 0:
            warning_parts.append(f"{skipped_groups} skipped (not owned)")
        console.print(Alert.warning(f"Sync group(s): {', '.join(warning_parts)}"))
    else:
        action = "would be " if dry_run else ""
        details_parts = [f"{total_added} tracks {action}added"]
        if total_removed > 0:
            details_parts.append(f"{total_removed} {action}removed")
        if total_skipped_removals > 0:
            details_parts.append(f"{total_skipped_removals} skipped (target-only)")
        console.print(
            Alert.success(
                "All syncs completed",
                details=", ".join(details_parts),
            )
        )

    console.print()
