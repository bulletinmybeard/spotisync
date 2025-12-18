from datetime import datetime

from src.config.models import ExcludeConfig, FiltersConfig, IncludeConfig
from src.spotify.models import SpotifyAlbum, SpotifyArtist, SpotifyTrack
from src.sync.filters import FilterEngine, _is_spotify_id, _matches_pattern


def _mock_track(
    track_id: str = "1234567890abcdefghijkl",
    name: str = "Track",
    artist_id: str = "artist123456789012345",
    artist_name: str = "Artist",
    album_id: str = "album1234567890123456",
    album_name: str = "Album",
    is_local: bool = False,
    is_podcast: bool = False,
    added_at: datetime | None = None,
) -> SpotifyTrack:
    return SpotifyTrack(
        id=track_id,
        uri=f"spotify:track:{track_id}",
        name=name,
        artists=[SpotifyArtist(id=artist_id, name=artist_name, uri="uri")],
        album=SpotifyAlbum(id=album_id, name=album_name, uri="uri"),
        is_local=is_local,
        is_podcast=is_podcast,
        added_at=added_at,
    )


class TestHelperFunctions:
    def test_is_spotify_id_valid(self) -> None:
        assert _is_spotify_id("1234567890abcdefghijkl") is True
        assert _is_spotify_id("0OdUWJ0sBjDrqHygGUXeCF") is True
        assert _is_spotify_id("ABCDEFGHIJKLMNOPQRSTUV") is True

    def test_is_spotify_id_invalid(self) -> None:
        assert _is_spotify_id("short") is False
        assert _is_spotify_id("") is False
        assert _is_spotify_id("1234567890abcdefghijkl!") is False
        assert _is_spotify_id("123456789012345678901") is False

    def test_matches_pattern_regex(self) -> None:
        assert _matches_pattern("Hello World", "World") is True
        assert _matches_pattern("Hello World", "(?i)world") is True
        assert _matches_pattern("Hello World", "^Hello") is True
        assert _matches_pattern("Hello World", "Goodbye") is False

    def test_matches_pattern_invalid_regex(self) -> None:
        assert _matches_pattern("test", "[invalid") is False


class TestFilterEngine:
    def test_filter_local_files(self) -> None:
        tracks = [
            _mock_track(track_id="1", is_local=False),
            _mock_track(track_id="2", is_local=True),
            _mock_track(track_id="3", is_local=False),
        ]
        engine = FilterEngine(FiltersConfig())

        result = engine._filter_local_files(tracks)

        assert len(result) == 2
        assert all(not t.is_local for t in result)

    def test_filter_podcasts(self) -> None:
        tracks = [
            _mock_track(track_id="1", is_podcast=False),
            _mock_track(track_id="2", is_podcast=True),
            _mock_track(track_id="3", is_podcast=False),
        ]
        engine = FilterEngine(FiltersConfig())

        result = engine._filter_podcasts(tracks)

        assert len(result) == 2
        assert all(not t.is_podcast for t in result)

    def test_filter_by_artist_id(self) -> None:
        excluded_artist_id = "excluded12345678901234"
        tracks = [
            _mock_track(track_id="1", artist_id=excluded_artist_id),
            _mock_track(track_id="2", artist_id="other123456789012345a"),
        ]
        config = FiltersConfig(exclude=ExcludeConfig(artists=[excluded_artist_id]))
        engine = FilterEngine(config)

        result = engine._filter_by_exclude(tracks)

        assert len(result) == 1
        assert result[0].id == "2"

    def test_filter_by_artist_regex(self) -> None:
        tracks = [
            _mock_track(track_id="1", artist_name="Christmas Choir"),
            _mock_track(track_id="2", artist_name="Regular Band"),
            _mock_track(track_id="3", artist_name="xmas songs"),
        ]
        config = FiltersConfig(exclude=ExcludeConfig(artists=["(?i)christmas", "(?i)xmas"]))
        engine = FilterEngine(config)

        result = engine._filter_by_exclude(tracks)

        assert len(result) == 1
        assert result[0].id == "2"

    def test_filter_by_album_id(self) -> None:
        excluded_album_id = "excluded12345678901234"
        tracks = [
            _mock_track(track_id="1", album_id=excluded_album_id),
            _mock_track(track_id="2", album_id="other123456789012345a"),
        ]
        config = FiltersConfig(exclude=ExcludeConfig(albums=[excluded_album_id]))
        engine = FilterEngine(config)

        result = engine._filter_by_exclude(tracks)

        assert len(result) == 1
        assert result[0].id == "2"

    def test_filter_by_track_name_regex(self) -> None:
        tracks = [
            _mock_track(track_id="1", name="Original Song"),
            _mock_track(track_id="2", name="Original Song (Remix)"),
            _mock_track(track_id="3", name="Live at Madison"),
        ]
        config = FiltersConfig(exclude=ExcludeConfig(tracks=["(?i)remix", "(?i)live"]))
        engine = FilterEngine(config)

        result = engine._filter_by_exclude(tracks)

        assert len(result) == 1
        assert result[0].id == "1"

    def test_filter_by_include_artist_id(self) -> None:
        included_artist_id = "included12345678901234"
        tracks = [
            _mock_track(track_id="1", artist_id=included_artist_id),
            _mock_track(track_id="2", artist_id="other1234567890123456"),
            _mock_track(track_id="3", artist_id=included_artist_id),
        ]
        config = FiltersConfig(include=IncludeConfig(artists=[included_artist_id]))
        engine = FilterEngine(config)

        result = engine._filter_by_include(tracks)

        assert len(result) == 2
        result_ids = {t.id for t in result}
        assert "1" in result_ids
        assert "3" in result_ids

    def test_filter_by_include_artist_regex(self) -> None:
        tracks = [
            _mock_track(track_id="1", artist_name="Radiohead"),
            _mock_track(track_id="2", artist_name="Coldplay"),
            _mock_track(track_id="3", artist_name="The Radio Dept."),
        ]
        config = FiltersConfig(include=IncludeConfig(artists=["(?i)radiohead"]))
        engine = FilterEngine(config)

        result = engine._filter_by_include(tracks)

        assert len(result) == 1
        assert result[0].id == "1"

    def test_filter_include_then_exclude(self) -> None:
        artist_id = "radiohead1234567890123"
        tracks = [
            _mock_track(track_id="1", artist_id=artist_id, name="Creep"),
            _mock_track(track_id="2", artist_id=artist_id, name="Creep (Remix)"),
            _mock_track(track_id="3", artist_id="other1234567890123456", name="Other Song"),
        ]
        config = FiltersConfig(
            include=IncludeConfig(artists=[artist_id]),
            exclude=ExcludeConfig(tracks=["(?i)remix"]),
        )
        engine = FilterEngine(config)

        result = engine.apply_filters(tracks)

        assert len(result) == 1
        assert result[0].id == "1"
        assert result[0].name == "Creep"

    def test_apply_all_filters(self) -> None:
        tracks = [
            _mock_track(track_id="1", is_local=True),
            _mock_track(track_id="2", is_podcast=True),
            _mock_track(track_id="3", name="Good Track"),
        ]
        config = FiltersConfig(skip_podcasts=True)
        engine = FilterEngine(config)

        result = engine.apply_filters(tracks)

        assert len(result) == 1
        assert result[0].id == "3"

    def test_get_filter_summary(self) -> None:
        config = FiltersConfig(
            skip_podcasts=True,
            include=IncludeConfig(artists=["inc1"]),
            exclude=ExcludeConfig(
                artists=["a1", "a2"],
                albums=["al1"],
                tracks=["t1", "t2", "t3"],
            ),
        )
        engine = FilterEngine(config)

        summary = engine.get_filter_summary()

        assert summary["skip_podcasts"] is True
        assert summary["include_artists"] == 1
        assert summary["exclude_artists"] == 2
        assert summary["exclude_albums"] == 1
        assert summary["exclude_tracks"] == 3
