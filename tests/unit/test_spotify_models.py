from src.spotify.models import SpotifyAlbum, SpotifyArtist, SpotifyPlaylist, SpotifyTrack


class TestSpotifyTrack:
    def test_from_spotify_dict(self, sample_track_data: dict) -> None:
        track = SpotifyTrack.from_spotify_dict(sample_track_data)

        assert track.id == "4iV5W9uYEdYUVa79Axb7Rh"
        assert track.uri == "spotify:track:4iV5W9uYEdYUVa79Axb7Rh"
        assert track.name == "Test Track"
        assert track.popularity == 75
        assert track.duration_ms == 210000
        assert track.is_local is False
        assert track.is_podcast is False
        assert len(track.artists) == 1
        assert track.artists[0].name == "Test Artist"
        assert track.album.name == "Test Album"

    def test_from_spotify_dict_with_added_at(self, sample_track_data: dict) -> None:
        track = SpotifyTrack.from_spotify_dict(sample_track_data)

        assert track.added_at is not None
        assert track.added_at.year == 2024
        assert track.added_at.month == 1
        assert track.added_at.day == 15

    def test_from_spotify_dict_local_file(self, sample_local_track_data: dict) -> None:
        track = SpotifyTrack.from_spotify_dict(sample_local_track_data)

        assert track.is_local is True
        assert track.is_podcast is False
        assert track.name == "Local Track"

    def test_from_spotify_dict_podcast(self, sample_podcast_data: dict) -> None:
        track = SpotifyTrack.from_spotify_dict(sample_podcast_data)

        assert track.is_podcast is True
        assert track.is_local is False
        assert track.name == "Podcast Episode"

    def test_artist_names_property(self) -> None:
        track = SpotifyTrack(
            id="test",
            uri="spotify:track:test",
            name="Test",
            artists=[
                SpotifyArtist(id="1", name="Artist One", uri="uri1"),
                SpotifyArtist(id="2", name="Artist Two", uri="uri2"),
            ],
            album=SpotifyAlbum(id="album", name="Album", uri="album_uri"),
        )

        assert track.artist_names == "Artist One, Artist Two"

    def test_from_spotify_dict_without_added_at(self) -> None:
        data = {
            "track": {
                "id": "test123",
                "uri": "spotify:track:test123",
                "name": "No Added At",
                "popularity": 50,
                "duration_ms": 200000,
                "is_local": False,
                "type": "track",
                "artists": [{"id": "a1", "name": "Artist", "uri": "uri"}],
                "album": {"id": "al1", "name": "Album", "uri": "uri"},
            }
        }
        track = SpotifyTrack.from_spotify_dict(data)

        assert track.added_at is None


class TestSpotifyPlaylist:
    def test_from_spotify_dict(self) -> None:
        data = {
            "id": "37i9dQZF1DXcBWIGoYBM5M",
            "name": "Today's Top Hits",
            "uri": "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M",
            "public": True,
            "description": "The hottest 50 tracks",
            "tracks": {"total": 50},
            "owner": {"id": "spotify"},
        }
        playlist = SpotifyPlaylist.from_spotify_dict(data)

        assert playlist.id == "37i9dQZF1DXcBWIGoYBM5M"
        assert playlist.name == "Today's Top Hits"
        assert playlist.public is True
        assert playlist.total_tracks == 50
        assert playlist.owner_id == "spotify"
        assert playlist.description == "The hottest 50 tracks"

    def test_from_spotify_dict_minimal(self) -> None:
        data = {
            "id": "test123",
            "name": "My Playlist",
            "uri": "spotify:playlist:test123",
            "owner": {"id": "user123"},
        }
        playlist = SpotifyPlaylist.from_spotify_dict(data)

        assert playlist.id == "test123"
        assert playlist.public is False
        assert playlist.total_tracks == 0
        assert playlist.description is None
