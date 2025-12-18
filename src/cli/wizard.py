from dataclasses import dataclass
import re
from typing import TypedDict
import webbrowser

from chalkbox import Alert, Spinner, Table, get_console
import click

from src.spotify.auth import SpotifyAuthManager
from src.spotify.client import SpotifyClient
from src.utils.logger import get_logger

SYNC_GROUP_NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

logger = get_logger(__name__)
console = get_console()

CANCEL_HINT = "[dim](Ctrl+C to cancel/exit)[/dim]"


class FilterOptions(TypedDict):
    skip_podcasts: bool


class PlaylistInfo(TypedDict):
    id: str
    name: str
    tracks: int


def run_oauth_flow(auth_manager: SpotifyAuthManager, max_attempts: int = 1) -> SpotifyClient:
    auth_url = auth_manager.get_auth_url()

    console.print("[bold]Authorize SpotiSync in your browser:[/bold]")
    console.print(f"[link={auth_url}]{auth_url}[/link]")
    console.print()

    try:
        webbrowser.open(auth_url)
        console.print("[dim]Browser opened automatically[/dim]")
    except Exception:
        console.print("[dim]Please open the URL manually[/dim]")

    console.print()
    console.print("[bold]After clicking 'Agree', paste the redirect URL:[/bold]")
    console.print("[dim]Example: https://example.com/callback?code=AQB...[/dim]")
    console.print()

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            redirect_url = click.prompt("Redirect URL", type=str).strip()
            auth_manager.authenticate_with_code(redirect_url)
            return SpotifyClient(auth_manager)
        except Exception as e:
            last_error = e
            if attempt < max_attempts:
                console.print(Alert.warning(f"Authentication failed: {e}"))
                console.print(f"[dim]Attempt {attempt}/{max_attempts}. Please try again.[/dim]")
                console.print()

    raise last_error or RuntimeError("Authentication failed")


@dataclass
class SyncGroupInput:
    name: str
    source: str
    target: str
    filters: FilterOptions | None = None


def fetch_user_playlists(spotify_client: SpotifyClient) -> list[PlaylistInfo]:
    try:
        playlists: list[PlaylistInfo] = []
        offset = 0
        limit = 50

        while True:
            results = spotify_client.sp.current_user_playlists(limit=limit, offset=offset)

            if not results or not results.get("items"):
                break

            for playlist in results["items"]:
                playlists.append(
                    PlaylistInfo(
                        id=playlist["id"],
                        name=playlist["name"],
                        tracks=playlist["tracks"]["total"],
                    )
                )

            if not results.get("next"):
                break

            offset += limit

        return playlists

    except Exception as e:
        logger.error(f"Error fetching playlists: {e}")
        return []


def prompt_sync_group_name(
    existing_names: list[str] | None = None, default: str = "my-sync"
) -> str:
    while True:
        name = click.prompt(
            "Name for this sync group (e.g., 'daily-liked-sync')",
            type=str,
            default=default,
        ).strip()

        if len(name) > 50:
            console.print(Alert.warning("Name too long. Maximum 50 characters."))
            continue

        if not SYNC_GROUP_NAME_PATTERN.match(name):
            console.print(
                Alert.warning(
                    "Invalid name format",
                    details="Use kebab-case: lowercase letters, numbers, and hyphens (e.g., 'my-sync-group')",
                )
            )
            continue

        if existing_names and name in existing_names:
            console.print(
                Alert.warning(f"Name '{name}' already exists. Please choose a different name.")
            )
            continue

        return name


def prompt_source(spotify_client: SpotifyClient) -> str:
    console.print()
    console.print("[bold]What should SpotiSync sync FROM?[/bold]")
    console.print("  [cyan]1.[/cyan] Liked Songs (your private collection)")
    console.print("  [cyan]2.[/cyan] A specific playlist")
    console.print()

    source_choice = click.prompt("Choose source", type=click.Choice(["1", "2"]), default="1")

    if source_choice == "1":
        return "liked_tracks"

    with Spinner("Fetching your playlists") as spinner:
        playlists = fetch_user_playlists(spotify_client)
        spinner.success(f"Found {len(playlists)} playlists")

    if not playlists:
        console.print(Alert.info("No playlists found. Using Liked Songs as source."))
        return "liked_tracks"

    console.print()
    playlist_table = Table(
        headers=["#", "Playlist Name", "Tracks"],
        title="Your Playlists",
    )
    for idx, playlist in enumerate(playlists[:20], 1):
        playlist_table.add_row(str(idx), playlist["name"], str(playlist["tracks"]))
    console.print(playlist_table)

    playlist_idx = click.prompt(
        "\nSelect source playlist number",
        type=click.IntRange(1, len(playlists[:20])),
        default=1,
    )
    return playlists[playlist_idx - 1]["id"]


def prompt_target(spotify_client: SpotifyClient) -> str:
    console.print()
    console.print("[bold]Where should SpotiSync sync TO?[/bold]")
    console.print()

    with Spinner("Fetching your playlists") as spinner:
        playlists = fetch_user_playlists(spotify_client)
        spinner.success(f"Found {len(playlists)} playlists")

    if playlists:
        console.print()
        playlist_table = Table(
            headers=["#", "Playlist Name", "Tracks"],
            title="Your Playlists",
        )
        for idx, playlist in enumerate(playlists[:20], 1):
            playlist_table.add_row(str(idx), playlist["name"], str(playlist["tracks"]))
        playlist_table.add_row(
            str(len(playlists[:20]) + 1),
            "[Create new playlist]",
            "-",
            severity="info",
        )
        console.print(playlist_table)

        choice = click.prompt(
            "\nSelect target playlist number",
            type=click.IntRange(1, len(playlists[:20]) + 1),
        )

        if choice <= len(playlists[:20]):
            return playlists[choice - 1]["id"]

        # Create new playlist
        playlist_name = click.prompt("Playlist name", type=str, default="SpotiSync Playlist")
        is_public = click.confirm("Make public?", default=False)

        with Spinner(f"Creating playlist '{playlist_name}'") as spinner:
            user = spotify_client.get_current_user()
            new_playlist = spotify_client.sp.user_playlist_create(
                user["id"], playlist_name, public=is_public
            )
            spinner.success(f"Created playlist: {playlist_name}")

        if new_playlist is None:
            raise RuntimeError(f"Failed to create playlist: {playlist_name}")
        return new_playlist["id"]

    console.print(Alert.info("No playlists found."))
    return click.prompt("Target playlist ID", type=str).strip()


def prompt_filters(use_defaults: bool = False) -> FilterOptions:
    if use_defaults:
        return FilterOptions(
            skip_podcasts=True,
        )

    console.print()
    console.print("[bold]Configure track filtering:[/bold]")
    console.print()

    skip_podcasts = click.confirm("Skip podcasts?", default=True)

    return FilterOptions(
        skip_podcasts=skip_podcasts,
    )


def prompt_sync_group(
    spotify_client: SpotifyClient,
    existing_names: list[str] | None = None,
    prompt_for_filters: bool = True,
) -> SyncGroupInput:
    name = prompt_sync_group_name(existing_names)
    source = prompt_source(spotify_client)
    target = prompt_target(spotify_client)

    filters = None
    if prompt_for_filters and click.confirm(
        "\nConfigure custom filters for this sync group?", default=False
    ):
        filters = prompt_filters()

    return SyncGroupInput(
        name=name,
        source=source,
        target=target,
        filters=filters,
    )
