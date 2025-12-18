from collections.abc import Callable
import time
from typing import Any, TypeVar

import spotipy
from spotipy.exceptions import SpotifyException

from src.spotify.auth import SpotifyAuthManager
from src.spotify.models import SpotifyPlaylist, SpotifyTrack
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SpotifyClient:
    # Spotify API limits
    MAX_TRACKS_PER_REQUEST = 100
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

    _T = TypeVar("_T")

    def __init__(self, auth_manager: SpotifyAuthManager) -> None:
        self.auth_manager = auth_manager
        self.sp = spotipy.Spotify(auth_manager=auth_manager.sp_oauth)

    def _retry_on_rate_limit(self, func: Callable[..., _T], *args: Any, **kwargs: Any) -> _T:
        for _attempt in range(self.MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except SpotifyException as e:
                if e.http_status == 429:  # Rate limit
                    retry_after = int(e.headers.get("Retry-After", self.RETRY_DELAY))
                    logger.warning(f"Rate limited, retrying in {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                elif e.http_status == 403:
                    raise SpotifyException(
                        403,
                        -1,
                        "Permission denied: You don't have write access to this playlist",
                    ) from None
                else:
                    raise
        raise SpotifyException(429, -1, "Max retries exceeded for rate limit")

    def get_liked_tracks(self, limit: int | None = None) -> list[SpotifyTrack]:
        logger.debug("Fetching liked tracks...")
        tracks = []
        offset = 0
        batch_size = 50  # Spotify API limit per request

        while True:
            try:
                results = self._retry_on_rate_limit(
                    self.sp.current_user_saved_tracks, limit=batch_size, offset=offset
                )

                if not results or not results["items"]:
                    break

                for item in results["items"]:
                    tracks.append(SpotifyTrack.from_spotify_dict(item))

                logger.debug(f"Fetched {len(tracks)} liked tracks so far...")

                # Check if we've fetched all or reached limit
                if not results["next"] or (limit and len(tracks) >= limit):
                    break

                offset += batch_size

            except Exception as e:
                logger.error(f"Error fetching liked tracks: {e}")
                raise

        logger.debug(f"Fetched {len(tracks)} liked tracks total")
        return tracks[:limit] if limit else tracks

    def get_playlist_tracks(self, playlist_id: str, limit: int | None = None) -> list[SpotifyTrack]:
        logger.debug(f"Fetching tracks from playlist: {playlist_id}")
        tracks = []
        offset = 0
        batch_size = 100  # Spotify API limit per request for playlists

        while True:
            try:
                results = self._retry_on_rate_limit(
                    self.sp.playlist_items,
                    playlist_id,
                    limit=batch_size,
                    offset=offset,
                    additional_types=["track"],
                )

                if not results or not results["items"]:
                    break

                for item in results["items"]:
                    if not item.get("track"):
                        continue
                    tracks.append(SpotifyTrack.from_spotify_dict(item))

                logger.debug(f"Fetched {len(tracks)} playlist tracks so far...")

                # Check if we've fetched all or reached limit
                if not results["next"] or (limit and len(tracks) >= limit):
                    break

                offset += batch_size

            except Exception as e:
                logger.error(f"Error fetching playlist tracks: {e}")
                raise

        logger.debug(f"Fetched {len(tracks)} playlist tracks total")
        return tracks[:limit] if limit else tracks

    def get_playlist(self, playlist_id: str) -> SpotifyPlaylist:
        try:
            results = self._retry_on_rate_limit(self.sp.playlist, playlist_id)
            return SpotifyPlaylist.from_spotify_dict(results)
        except Exception as e:
            logger.error(f"Error fetching playlist metadata: {e}")
            raise

    def add_tracks_to_playlist(self, playlist_id: str, track_uris: list[str]) -> None:
        if not track_uris:
            return

        logger.info(f"Adding {len(track_uris)} tracks to playlist...")

        for i in range(0, len(track_uris), self.MAX_TRACKS_PER_REQUEST):
            batch = track_uris[i : i + self.MAX_TRACKS_PER_REQUEST]
            try:
                self._retry_on_rate_limit(self.sp.playlist_add_items, playlist_id, batch)
                logger.debug(f"Added batch of {len(batch)} tracks")
            except Exception as e:
                logger.error(f"Error adding tracks to playlist: {e}")
                raise

        logger.info(f"Successfully added {len(track_uris)} tracks")

    def remove_tracks_from_playlist(self, playlist_id: str, track_uris: list[str]) -> None:
        if not track_uris:
            return

        logger.info(f"Removing {len(track_uris)} tracks from playlist...")

        for i in range(0, len(track_uris), self.MAX_TRACKS_PER_REQUEST):
            batch = track_uris[i : i + self.MAX_TRACKS_PER_REQUEST]
            try:
                self._retry_on_rate_limit(
                    self.sp.playlist_remove_all_occurrences_of_items, playlist_id, batch
                )
                logger.debug(f"Removed batch of {len(batch)} tracks")
            except Exception as e:
                logger.error(f"Error removing tracks from playlist: {e}")
                raise

        logger.info(f"Successfully removed {len(track_uris)} tracks")

    def clear_playlist(self, playlist_id: str) -> None:
        logger.info("Clearing playlist...")
        tracks = self.get_playlist_tracks(playlist_id)
        if tracks:
            track_uris = [track.uri for track in tracks]
            self.remove_tracks_from_playlist(playlist_id, track_uris)
        logger.info("Playlist cleared")

    def get_current_user(self) -> dict[str, Any]:
        try:
            return self._retry_on_rate_limit(self.sp.current_user)
        except Exception as e:
            logger.error(f"Error fetching current user: {e}")
            raise

    def validate_playlist_ownership(self, playlist_id: str) -> tuple[bool, str, str]:
        user = self.get_current_user()
        playlist = self.get_playlist(playlist_id)
        is_owner = user["id"] == playlist.owner_id
        return (is_owner, playlist.name, playlist.owner_id)
