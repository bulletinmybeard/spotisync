import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

SPOTIFY_ID_PATTERN = re.compile(r"^[a-zA-Z0-9]{22}$")
SYNC_GROUP_NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class SpotifyConfig(BaseModel):
    client_id: str = Field(min_length=1)
    client_secret: str = Field(min_length=1)
    redirect_uri: str = "https://example.com/callback"
    scopes: list[str] = Field(
        default_factory=lambda: [
            "user-library-read",
            "playlist-read-private",
            "playlist-modify-public",
            "playlist-modify-private",
        ],
    )

    @field_validator("redirect_uri")
    @classmethod
    def validate_redirect_uri(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("redirect_uri must start with http:// or https://")
        return v


class IncludeConfig(BaseModel):
    artists: list[str] = Field(default_factory=list)
    tracks: list[str] = Field(default_factory=list)


class ExcludeConfig(BaseModel):
    artists: list[str] = Field(default_factory=list)
    albums: list[str] = Field(default_factory=list)
    tracks: list[str] = Field(default_factory=list)


class FiltersConfig(BaseModel):
    skip_podcasts: bool = True
    include: IncludeConfig = Field(default_factory=IncludeConfig)
    exclude: ExcludeConfig = Field(default_factory=ExcludeConfig)

    @model_validator(mode="after")
    def validate_no_artist_overlap(self) -> "FiltersConfig":
        overlap = set(self.include.artists) & set(self.exclude.artists)
        if overlap:
            raise ValueError(
                f"Artist patterns cannot appear in both include and exclude: {overlap}"
            )
        return self


class CronConfig(BaseModel):
    enabled: bool = False
    schedule: str = "*/10 * * * *"

    @field_validator("schedule")
    @classmethod
    def validate_cron_expression(cls, v: str) -> str:
        parts = v.split()
        if len(parts) != 5:
            raise ValueError(
                f"Invalid cron expression '{v}'. Must have 5 fields: minute hour day month weekday"
            )
        return v


class SyncGroupConfig(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    disabled: bool = False
    skip_removals: bool = False
    filters: FiltersConfig | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not SYNC_GROUP_NAME_PATTERN.match(v):
            raise ValueError(
                f"Invalid name '{v}'. Must be kebab-case: lowercase letters, numbers, "
                "and hyphens (e.g., 'my-sync-group')"
            )
        return v

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if v == "liked_tracks":
            return v
        if v.startswith("spotify:playlist:"):
            return v.split(":")[-1]
        if not SPOTIFY_ID_PATTERN.match(v):
            raise ValueError(
                f"Invalid source '{v}'. Must be 'liked_tracks' or a valid Spotify playlist ID"
            )
        return v

    @field_validator("target")
    @classmethod
    def validate_target(cls, v: str) -> str:
        if v.startswith("spotify:playlist:"):
            v = v.split(":")[-1]
        if not SPOTIFY_ID_PATTERN.match(v):
            raise ValueError(f"Invalid target playlist ID '{v}'")
        return v


class SpotiSyncConfig(BaseModel):
    spotify: SpotifyConfig
    filters: FiltersConfig = Field(default_factory=FiltersConfig)
    cron: CronConfig = Field(default_factory=CronConfig)
    sync_groups: list[SyncGroupConfig] = Field(min_length=1)

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
    }

    @model_validator(mode="after")
    def validate_unique_names(self) -> "SpotiSyncConfig":
        names = [g.name for g in self.sync_groups]
        duplicates = [name for name in names if names.count(name) > 1]
        if duplicates:
            raise ValueError(f"Duplicate sync group names: {set(duplicates)}")
        return self

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def get_enabled_sync_groups(self) -> list[SyncGroupConfig]:
        return [g for g in self.sync_groups if not g.disabled]
