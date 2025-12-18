from src.config.models import FiltersConfig, SyncGroupConfig
from src.spotify.client import SpotifyClient
from src.spotify.models import SpotifyTrack
from src.sync.diff import SyncDiff, calculate_diff
from src.sync.filters import FilterEngine
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SyncEngine:
    def __init__(
        self,
        spotify_client: SpotifyClient,
        sync_group: SyncGroupConfig,
        filters: FiltersConfig,
    ) -> None:
        self.spotify_client = spotify_client
        self.sync_group = sync_group
        self.filters = filters
        self.filter_engine = FilterEngine(filters)

    @property
    def name(self) -> str:
        return self.sync_group.name

    @property
    def source(self) -> str:
        return self.sync_group.source

    @property
    def target(self) -> str:
        return self.sync_group.target

    def run_sync(self, dry_run: bool = False) -> SyncDiff:
        logger.debug(f"Starting sync: {self.name}")

        source_tracks = self._fetch_source_tracks()
        filtered_source_tracks = self.filter_engine.apply_filters(source_tracks)
        target_tracks = self._fetch_target_tracks()
        diff = calculate_diff(filtered_source_tracks, target_tracks)
        self._display_summary(diff, dry_run)

        if not dry_run:
            if diff.has_changes:
                self._apply_changes(diff)
            else:
                logger.debug("No changes to apply, playlists are already in sync")
        else:
            logger.debug("DRY RUN - No changes applied")

        logger.debug(f"Sync completed: {self.name}")

        return diff

    def _fetch_source_tracks(self) -> list[SpotifyTrack]:
        if self.source == "liked_tracks":
            logger.debug("Fetching source: Liked Tracks")
            return self.spotify_client.get_liked_tracks()
        else:
            logger.debug(f"Fetching source: Playlist {self.source}")
            return self.spotify_client.get_playlist_tracks(self.source)

    def _fetch_target_tracks(self) -> list[SpotifyTrack]:
        logger.debug(f"Fetching target: Playlist {self.target}")
        return self.spotify_client.get_playlist_tracks(self.target)

    def _display_summary(self, diff: SyncDiff, dry_run: bool) -> None:
        logger.debug("")
        logger.debug(f"Sync Summary ({self.name}):")
        logger.debug("-" * 60)
        logger.debug(f"  Additions: {len(diff.additions)} tracks")
        logger.debug(f"  Removals:  {len(diff.removals)} tracks")
        logger.debug(f"  Unchanged: {len(diff.unchanged)} tracks")
        logger.debug(f"  Total changes: {diff.total_changes}")
        logger.debug("-" * 60)

        if dry_run:
            logger.debug("DRY RUN MODE - Changes will not be applied")

            if diff.additions:
                logger.debug("")
                logger.debug("Tracks to be added:")
                for track in diff.additions[:10]:
                    logger.debug(f"  + {track.name} - {track.artist_names}")
                if len(diff.additions) > 10:
                    logger.debug(f"  ... and {len(diff.additions) - 10} more")

            if diff.removals:
                logger.debug("")
                if self.sync_group.skip_removals:
                    logger.debug("Target-only tracks (will be kept due to skip_removals):")
                    for track in diff.removals[:10]:
                        logger.debug(f"  ~ {track.name} - {track.artist_names}")
                else:
                    logger.debug("Tracks to be removed:")
                    for track in diff.removals[:10]:
                        logger.debug(f"  - {track.name} - {track.artist_names}")
                if len(diff.removals) > 10:
                    logger.debug(f"  ... and {len(diff.removals) - 10} more")

    def _apply_changes(self, diff: SyncDiff) -> None:
        logger.debug("Applying changes (incremental sync)")

        if diff.additions:
            logger.debug(f"Adding {len(diff.additions)} new tracks...")
            track_uris = [track.uri for track in diff.additions]
            self.spotify_client.add_tracks_to_playlist(self.target, track_uris)

        if diff.removals:
            if self.sync_group.skip_removals:
                logger.debug(
                    f"Skipping removal of {len(diff.removals)} target-only tracks (skip_removals enabled)"
                )
            else:
                logger.debug(f"Removing {len(diff.removals)} tracks...")
                track_uris = [track.uri for track in diff.removals]
                self.spotify_client.remove_tracks_from_playlist(self.target, track_uris)

        logger.debug("Changes applied successfully")

    def get_source_info(self) -> dict[str, str]:
        if self.source == "liked_tracks":
            return {
                "type": "Liked Tracks",
                "id": "N/A",
                "description": "Your personal liked tracks collection",
            }
        else:
            try:
                playlist = self.spotify_client.get_playlist(self.source)
                return {
                    "type": "Playlist",
                    "id": playlist.id,
                    "name": playlist.name,
                    "description": playlist.description or "No description",
                    "total_tracks": str(playlist.total_tracks),
                }
            except Exception as e:
                logger.error(f"Error fetching source playlist info: {e}")
                return {
                    "type": "Playlist",
                    "id": self.source,
                    "error": str(e),
                }

    def get_target_info(self) -> dict[str, str]:
        try:
            playlist = self.spotify_client.get_playlist(self.target)
            return {
                "id": playlist.id,
                "name": playlist.name,
                "description": playlist.description or "No description",
                "total_tracks": str(playlist.total_tracks),
                "public": "Yes" if playlist.public else "No",
            }
        except Exception as e:
            logger.error(f"Error fetching target playlist info: {e}")
            return {
                "id": self.target,
                "error": str(e),
            }
