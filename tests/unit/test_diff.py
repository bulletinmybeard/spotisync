from src.spotify.models import SpotifyAlbum, SpotifyArtist, SpotifyTrack
from src.sync.diff import SyncDiff, calculate_diff


def _mock_track(track_id: str, name: str = "Track") -> SpotifyTrack:
    return SpotifyTrack(
        id=track_id,
        uri=f"spotify:track:{track_id}",
        name=name,
        artists=[SpotifyArtist(id="artist1", name="Artist", uri="uri")],
        album=SpotifyAlbum(id="album1", name="Album", uri="uri"),
    )


class TestSyncDiff:
    def test_has_changes_with_additions(self) -> None:
        diff = SyncDiff(
            additions=[_mock_track("1")],
            removals=[],
            unchanged=[],
        )

        assert diff.has_changes is True

    def test_has_changes_with_removals(self) -> None:
        diff = SyncDiff(
            additions=[],
            removals=[_mock_track("1")],
            unchanged=[],
        )

        assert diff.has_changes is True

    def test_has_changes_none(self) -> None:
        diff = SyncDiff(
            additions=[],
            removals=[],
            unchanged=[_mock_track("1")],
        )

        assert diff.has_changes is False

    def test_total_changes(self) -> None:
        diff = SyncDiff(
            additions=[_mock_track("1"), _mock_track("2")],
            removals=[_mock_track("3")],
            unchanged=[_mock_track("4")],
        )

        assert diff.total_changes == 3

    def test_summary(self) -> None:
        diff = SyncDiff(
            additions=[_mock_track("1"), _mock_track("2")],
            removals=[_mock_track("3")],
            unchanged=[_mock_track("4"), _mock_track("5")],
        )

        summary = diff.summary()

        assert "Additions: 2" in summary
        assert "Removals: 1" in summary
        assert "Unchanged: 2" in summary
        assert "Total changes: 3" in summary


class TestCalculateDiff:
    def test_all_new_tracks(self) -> None:
        source = [_mock_track("1"), _mock_track("2")]
        target: list[SpotifyTrack] = []

        diff = calculate_diff(source, target)

        assert len(diff.additions) == 2
        assert len(diff.removals) == 0
        assert len(diff.unchanged) == 0

    def test_all_removals(self) -> None:
        source: list[SpotifyTrack] = []
        target = [_mock_track("1"), _mock_track("2")]

        diff = calculate_diff(source, target)

        assert len(diff.additions) == 0
        assert len(diff.removals) == 2
        assert len(diff.unchanged) == 0

    def test_no_changes(self) -> None:
        tracks = [_mock_track("1"), _mock_track("2")]

        diff = calculate_diff(tracks, tracks)

        assert len(diff.additions) == 0
        assert len(diff.removals) == 0
        assert len(diff.unchanged) == 2
        assert diff.has_changes is False

    def test_mixed_changes(self) -> None:
        source = [_mock_track("1"), _mock_track("2"), _mock_track("3")]
        target = [_mock_track("2"), _mock_track("4")]

        diff = calculate_diff(source, target)

        assert len(diff.additions) == 2
        assert len(diff.removals) == 1
        assert len(diff.unchanged) == 1

        addition_ids = {t.id for t in diff.additions}
        assert "1" in addition_ids
        assert "3" in addition_ids

        removal_ids = {t.id for t in diff.removals}
        assert "4" in removal_ids

        unchanged_ids = {t.id for t in diff.unchanged}
        assert "2" in unchanged_ids
