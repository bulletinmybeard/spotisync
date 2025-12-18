import re

from src.config.models import ExcludeConfig, FiltersConfig, IncludeConfig
from src.spotify.models import SpotifyTrack
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Spotify IDs are 22 characters, alphanumeric
SPOTIFY_ID_PATTERN = re.compile(r"^[a-zA-Z0-9]{22}$")


def _is_spotify_id(value: str) -> bool:
    return bool(SPOTIFY_ID_PATTERN.match(value))


def _matches_pattern(value: str, pattern: str) -> bool:
    if _is_spotify_id(pattern):
        return value == pattern
    try:
        return bool(re.search(pattern, value))
    except re.error:
        logger.warning(f"Invalid regex pattern: {pattern}")
        return False


class FilterEngine:
    def __init__(self, config: FiltersConfig) -> None:
        self.config = config

    def apply_filters(self, tracks: list[SpotifyTrack]) -> list[SpotifyTrack]:
        logger.debug(f"Applying filters to {len(tracks)} tracks...")
        original_count = len(tracks)

        tracks = self._filter_local_files(tracks)

        if self.config.skip_podcasts:
            tracks = self._filter_podcasts(tracks)

        if self._has_include_filters():
            tracks = self._filter_by_include(tracks)

        if self._has_exclude_filters():
            tracks = self._filter_by_exclude(tracks)

        filtered_count = original_count - len(tracks)
        if filtered_count > 0:
            logger.debug(f"Filtered out {filtered_count} tracks, {len(tracks)} remaining")
        else:
            logger.debug(f"No tracks filtered, {len(tracks)} tracks remaining")

        return tracks

    def _has_include_filters(self) -> bool:
        include = self.config.include
        return bool(include.artists or include.tracks)

    def _has_exclude_filters(self) -> bool:
        exclude = self.config.exclude
        return bool(exclude.artists or exclude.albums or exclude.tracks)

    @staticmethod
    def _filter_local_files(tracks: list[SpotifyTrack]) -> list[SpotifyTrack]:
        before = len(tracks)
        filtered = [track for track in tracks if not track.is_local]
        removed = before - len(filtered)

        if removed > 0:
            logger.debug(f"Filtered out {removed} local files")

        return filtered

    @staticmethod
    def _filter_podcasts(tracks: list[SpotifyTrack]) -> list[SpotifyTrack]:
        before = len(tracks)
        filtered = [track for track in tracks if not track.is_podcast]
        removed = before - len(filtered)

        if removed > 0:
            logger.debug(f"Filtered out {removed} podcast episodes")

        return filtered

    def _filter_by_include(self, tracks: list[SpotifyTrack]) -> list[SpotifyTrack]:
        include = self.config.include
        before = len(tracks)

        filtered = []
        for track in tracks:
            if self._matches_include(track, include):
                filtered.append(track)

        removed = before - len(filtered)
        if removed > 0:
            logger.debug(f"Include filter kept {len(filtered)} tracks, excluded {removed}")

        return filtered

    @staticmethod
    def _matches_include(track: SpotifyTrack, include: IncludeConfig) -> bool:
        if include.artists:
            for pattern in include.artists:
                for artist in track.artists:
                    if _is_spotify_id(pattern):
                        if artist.id == pattern:
                            return True
                    elif _matches_pattern(artist.name, pattern):
                        return True

        if include.tracks:
            for pattern in include.tracks:
                if _matches_pattern(track.name, pattern):
                    return True

        return False

    def _filter_by_exclude(self, tracks: list[SpotifyTrack]) -> list[SpotifyTrack]:
        exclude = self.config.exclude
        before = len(tracks)

        filtered = []
        excluded_artists = 0
        excluded_albums = 0
        excluded_tracks = 0

        for track in tracks:
            if exclude.artists and self._matches_artist_exclude(track, exclude):
                excluded_artists += 1
                continue

            if exclude.albums and self._matches_album_exclude(track, exclude):
                excluded_albums += 1
                continue

            if exclude.tracks and self._matches_track_exclude(track, exclude):
                excluded_tracks += 1
                continue

            filtered.append(track)

        removed = before - len(filtered)
        if removed > 0:
            details = []
            if excluded_artists:
                details.append(f"{excluded_artists} by artist")
            if excluded_albums:
                details.append(f"{excluded_albums} by album")
            if excluded_tracks:
                details.append(f"{excluded_tracks} by track name")
            logger.debug(f"Excluded {removed} tracks: {', '.join(details)}")

        return filtered

    @staticmethod
    def _matches_artist_exclude(track: SpotifyTrack, exclude: ExcludeConfig) -> bool:
        for pattern in exclude.artists:
            for artist in track.artists:
                if _is_spotify_id(pattern):
                    if artist.id == pattern:
                        return True
                elif _matches_pattern(artist.name, pattern):
                    return True
        return False

    @staticmethod
    def _matches_album_exclude(track: SpotifyTrack, exclude: ExcludeConfig) -> bool:
        for pattern in exclude.albums:
            if _is_spotify_id(pattern):
                if track.album.id == pattern:
                    return True
            elif _matches_pattern(track.album.name, pattern):
                return True
        return False

    @staticmethod
    def _matches_track_exclude(track: SpotifyTrack, exclude: ExcludeConfig) -> bool:
        return any(_matches_pattern(track.name, pattern) for pattern in exclude.tracks)

    def get_filter_summary(self) -> dict[str, bool | int]:
        return {
            "skip_local_files": True,
            "skip_podcasts": self.config.skip_podcasts,
            "include_artists": len(self.config.include.artists),
            "include_tracks": len(self.config.include.tracks),
            "exclude_artists": len(self.config.exclude.artists),
            "exclude_albums": len(self.config.exclude.albums),
            "exclude_tracks": len(self.config.exclude.tracks),
        }
