from datetime import UTC, datetime

import pytest

from src.config.models import ExcludeConfig, FiltersConfig
from src.spotify.models import SpotifyAlbum, SpotifyArtist, SpotifyTrack


@pytest.fixture
def sample_track_data() -> dict:
    return {
        "added_at": "2024-01-15T10:30:00Z",
        "track": {
            "id": "4iV5W9uYEdYUVa79Axb7Rh",
            "uri": "spotify:track:4iV5W9uYEdYUVa79Axb7Rh",
            "name": "Test Track",
            "popularity": 75,
            "duration_ms": 210000,
            "is_local": False,
            "type": "track",
            "artists": [
                {
                    "id": "0OdUWJ0sBjDrqHygGUXeCF",
                    "name": "Test Artist",
                    "uri": "spotify:artist:0OdUWJ0sBjDrqHygGUXeCF",
                }
            ],
            "album": {
                "id": "6akEvsycLGftJxYudPjmqK",
                "name": "Test Album",
                "uri": "spotify:album:6akEvsycLGftJxYudPjmqK",
            },
        },
    }


@pytest.fixture
def sample_local_track_data() -> dict:
    return {
        "added_at": "2024-01-10T08:00:00Z",
        "track": {
            "id": "",
            "uri": "spotify:local:Artist:Album:Track:180000",
            "name": "Local Track",
            "popularity": 0,
            "duration_ms": 180000,
            "is_local": True,
            "type": "track",
            "artists": [{"id": "", "name": "Local Artist", "uri": ""}],
            "album": {"id": "", "name": "Local Album", "uri": ""},
        },
    }


@pytest.fixture
def sample_podcast_data() -> dict:
    return {
        "added_at": "2024-01-12T14:00:00Z",
        "track": {
            "id": "1234567890abcdefghijkl",
            "uri": "spotify:episode:1234567890abcdefghijkl",
            "name": "Podcast Episode",
            "popularity": 50,
            "duration_ms": 3600000,
            "is_local": False,
            "type": "episode",
            "artists": [{"id": "", "name": "Podcast Host", "uri": ""}],
            "album": {"id": "", "name": "Podcast Show", "uri": ""},
        },
    }


@pytest.fixture
def sample_spotify_track() -> SpotifyTrack:
    return SpotifyTrack(
        id="4iV5W9uYEdYUVa79Axb7Rh",
        uri="spotify:track:4iV5W9uYEdYUVa79Axb7Rh",
        name="Test Track",
        artists=[
            SpotifyArtist(
                id="0OdUWJ0sBjDrqHygGUXeCF",
                name="Test Artist",
                uri="spotify:artist:0OdUWJ0sBjDrqHygGUXeCF",
            )
        ],
        album=SpotifyAlbum(
            id="6akEvsycLGftJxYudPjmqK",
            name="Test Album",
            uri="spotify:album:6akEvsycLGftJxYudPjmqK",
        ),
        added_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        popularity=75,
        is_local=False,
        is_podcast=False,
        duration_ms=210000,
    )


@pytest.fixture
def sample_filters_config() -> FiltersConfig:
    return FiltersConfig(
        skip_podcasts=True,
        exclude=ExcludeConfig(artists=[], albums=[], tracks=[]),
    )


@pytest.fixture
def filters_config_with_excludes() -> FiltersConfig:
    return FiltersConfig(
        skip_podcasts=True,
        exclude=ExcludeConfig(
            artists=["0OdUWJ0sBjDrqHygGUXeCF", "(?i)christmas"],
            albums=["6akEvsycLGftJxYudPjmqK"],
            tracks=["(?i)remix", "(?i)live"],
        ),
    )
