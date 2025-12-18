from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SpotifyArtist(BaseModel):
    id: str
    name: str
    uri: str


class SpotifyAlbum(BaseModel):
    id: str
    name: str
    uri: str


class SpotifyTrack(BaseModel):
    id: str
    uri: str
    name: str
    artists: list[SpotifyArtist]
    album: SpotifyAlbum
    added_at: datetime | None = None
    popularity: int = Field(default=0, ge=0, le=100)
    is_local: bool = False
    is_podcast: bool = False
    duration_ms: int = 0

    @property
    def artist_names(self) -> str:
        return ", ".join(artist.name for artist in self.artists)

    @classmethod
    def from_spotify_dict(cls, data: dict[str, Any]) -> "SpotifyTrack":
        track = data.get("track", data)

        added_at_str = data.get("added_at")
        added_at = (
            datetime.fromisoformat(added_at_str.replace("Z", "+00:00")) if added_at_str else None
        )

        is_local = track.get("is_local", False)
        is_podcast = track.get("type") == "episode"

        artists = [
            SpotifyArtist(
                id=artist.get("id", ""),
                name=artist.get("name", "Unknown Artist"),
                uri=artist.get("uri", ""),
            )
            for artist in track.get("artists", [])
        ]

        album_data = track.get("album", {})
        album = SpotifyAlbum(
            id=album_data.get("id", ""),
            name=album_data.get("name", "Unknown Album"),
            uri=album_data.get("uri", ""),
        )

        return cls(
            id=track.get("id", ""),
            uri=track.get("uri", ""),
            name=track.get("name", "Unknown Track"),
            artists=artists,
            album=album,
            added_at=added_at,
            popularity=track.get("popularity", 0),
            is_local=is_local,
            is_podcast=is_podcast,
            duration_ms=track.get("duration_ms", 0),
        )


class SpotifyPlaylist(BaseModel):
    id: str
    name: str
    uri: str
    public: bool = False
    total_tracks: int = 0
    description: str | None = None
    owner_id: str

    @classmethod
    def from_spotify_dict(cls, data: dict[str, Any]) -> "SpotifyPlaylist":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", "Unknown Playlist"),
            uri=data.get("uri", ""),
            public=data.get("public", False),
            total_tracks=data.get("tracks", {}).get("total", 0),
            description=data.get("description"),
            owner_id=data.get("owner", {}).get("id", ""),
        )
