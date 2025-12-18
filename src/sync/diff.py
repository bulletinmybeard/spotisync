from dataclasses import dataclass

from src.spotify.models import SpotifyTrack
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SyncDiff:
    additions: list[SpotifyTrack]
    removals: list[SpotifyTrack]
    unchanged: list[SpotifyTrack]

    @property
    def has_changes(self) -> bool:
        return len(self.additions) > 0 or len(self.removals) > 0

    @property
    def total_changes(self) -> int:
        return len(self.additions) + len(self.removals)

    def summary(self) -> str:
        lines = [
            f"Additions: {len(self.additions)}",
            f"Removals: {len(self.removals)}",
            f"Unchanged: {len(self.unchanged)}",
            f"Total changes: {self.total_changes}",
        ]
        return "\n".join(lines)


def calculate_diff(
    source_tracks: list[SpotifyTrack],
    target_tracks: list[SpotifyTrack],
) -> SyncDiff:
    logger.debug("Calculating sync diff...")

    source_uris = {track.uri for track in source_tracks}
    target_uris = {track.uri for track in target_tracks}

    source_tracks_dict = {track.uri: track for track in source_tracks}
    target_tracks_dict = {track.uri: track for track in target_tracks}

    addition_uris = source_uris - target_uris
    additions = [source_tracks_dict[uri] for uri in addition_uris]
    logger.debug(f"Found {len(additions)} tracks to add")

    removal_uris = target_uris - source_uris
    removals = [target_tracks_dict[uri] for uri in removal_uris]
    logger.debug(f"Found {len(removals)} tracks to remove")

    unchanged_uris = source_uris & target_uris
    unchanged = [source_tracks_dict[uri] for uri in unchanged_uris]
    logger.debug(f"Found {len(unchanged)} unchanged tracks")

    diff = SyncDiff(additions=additions, removals=removals, unchanged=unchanged)

    logger.debug(
        f"Diff calculated: {diff.total_changes} changes ({len(additions)} additions, {len(removals)} removals)"
    )

    return diff
