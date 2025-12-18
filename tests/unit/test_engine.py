from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from src.config.models import FiltersConfig, SyncGroupConfig
from src.spotify.models import SpotifyAlbum, SpotifyArtist, SpotifyTrack
from src.sync.engine import SyncEngine


def make_track(track_id: str, name: str) -> SpotifyTrack:
    return SpotifyTrack(
        id=track_id,
        uri=f"spotify:track:{track_id}",
        name=name,
        artists=[
            SpotifyArtist(
                id="artist123456789012345",
                name="Test Artist",
                uri="spotify:artist:artist123456789012345",
            )
        ],
        album=SpotifyAlbum(
            id="album1234567890123456",
            name="Test Album",
            uri="spotify:album:album1234567890123456",
        ),
        added_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        popularity=75,
        is_local=False,
        is_podcast=False,
        duration_ms=210000,
    )


@pytest.fixture
def mock_spotify_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def filters_config() -> FiltersConfig:
    return FiltersConfig()


class TestSyncEngineSkipRemovals:
    def test_removals_applied_when_skip_removals_false(
        self, mock_spotify_client: MagicMock, filters_config: FiltersConfig
    ) -> None:
        sync_group = SyncGroupConfig(
            name="test-sync",
            source="liked_tracks",
            target="1234567890abcdefghijkl",
            skip_removals=False,
        )

        source_tracks = [make_track("track1234567890123456", "Track 1")]
        target_tracks = [
            make_track("track1234567890123456", "Track 1"),
            make_track("track2345678901234567", "Track 2"),
        ]

        mock_spotify_client.get_liked_tracks.return_value = source_tracks
        mock_spotify_client.get_playlist_tracks.return_value = target_tracks

        engine = SyncEngine(mock_spotify_client, sync_group, filters_config)
        diff = engine.run_sync(dry_run=False)

        assert len(diff.removals) == 1
        assert diff.removals[0].name == "Track 2"
        mock_spotify_client.remove_tracks_from_playlist.assert_called_once()

    def test_removals_skipped_when_skip_removals_true(
        self, mock_spotify_client: MagicMock, filters_config: FiltersConfig
    ) -> None:
        sync_group = SyncGroupConfig(
            name="test-sync",
            source="liked_tracks",
            target="1234567890abcdefghijkl",
            skip_removals=True,
        )

        source_tracks = [make_track("track1234567890123456", "Track 1")]
        target_tracks = [
            make_track("track1234567890123456", "Track 1"),
            make_track("track2345678901234567", "Track 2"),
        ]

        mock_spotify_client.get_liked_tracks.return_value = source_tracks
        mock_spotify_client.get_playlist_tracks.return_value = target_tracks

        engine = SyncEngine(mock_spotify_client, sync_group, filters_config)
        diff = engine.run_sync(dry_run=False)

        assert len(diff.removals) == 1
        assert diff.removals[0].name == "Track 2"
        mock_spotify_client.remove_tracks_from_playlist.assert_not_called()

    def test_additions_still_work_with_skip_removals_true(
        self, mock_spotify_client: MagicMock, filters_config: FiltersConfig
    ) -> None:
        sync_group = SyncGroupConfig(
            name="test-sync",
            source="liked_tracks",
            target="1234567890abcdefghijkl",
            skip_removals=True,
        )

        source_tracks = [
            make_track("track1234567890123456", "Track 1"),
            make_track("track2345678901234567", "Track 2"),
        ]
        target_tracks = [make_track("track1234567890123456", "Track 1")]

        mock_spotify_client.get_liked_tracks.return_value = source_tracks
        mock_spotify_client.get_playlist_tracks.return_value = target_tracks

        engine = SyncEngine(mock_spotify_client, sync_group, filters_config)
        diff = engine.run_sync(dry_run=False)

        assert len(diff.additions) == 1
        assert diff.additions[0].name == "Track 2"
        mock_spotify_client.add_tracks_to_playlist.assert_called_once()

    def test_both_additions_and_skipped_removals(
        self, mock_spotify_client: MagicMock, filters_config: FiltersConfig
    ) -> None:
        sync_group = SyncGroupConfig(
            name="test-sync",
            source="liked_tracks",
            target="1234567890abcdefghijkl",
            skip_removals=True,
        )

        source_tracks = [
            make_track("track1234567890123456", "Track 1"),
            make_track("track3456789012345678", "Track 3"),
        ]
        target_tracks = [
            make_track("track1234567890123456", "Track 1"),
            make_track("track2345678901234567", "Track 2"),
        ]

        mock_spotify_client.get_liked_tracks.return_value = source_tracks
        mock_spotify_client.get_playlist_tracks.return_value = target_tracks

        engine = SyncEngine(mock_spotify_client, sync_group, filters_config)
        diff = engine.run_sync(dry_run=False)

        assert len(diff.additions) == 1
        assert len(diff.removals) == 1
        assert len(diff.unchanged) == 1
        mock_spotify_client.add_tracks_to_playlist.assert_called_once()
        mock_spotify_client.remove_tracks_from_playlist.assert_not_called()

    def test_dry_run_does_not_apply_changes_regardless_of_skip_removals(
        self, mock_spotify_client: MagicMock, filters_config: FiltersConfig
    ) -> None:
        sync_group = SyncGroupConfig(
            name="test-sync",
            source="liked_tracks",
            target="1234567890abcdefghijkl",
            skip_removals=False,
        )

        source_tracks = [make_track("track1234567890123456", "Track 1")]
        target_tracks = [
            make_track("track1234567890123456", "Track 1"),
            make_track("track2345678901234567", "Track 2"),
        ]

        mock_spotify_client.get_liked_tracks.return_value = source_tracks
        mock_spotify_client.get_playlist_tracks.return_value = target_tracks

        engine = SyncEngine(mock_spotify_client, sync_group, filters_config)
        diff = engine.run_sync(dry_run=True)

        assert len(diff.removals) == 1
        mock_spotify_client.add_tracks_to_playlist.assert_not_called()
        mock_spotify_client.remove_tracks_from_playlist.assert_not_called()
