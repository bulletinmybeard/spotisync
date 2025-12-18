from pydantic import ValidationError
import pytest

from src.config.models import (
    CronConfig,
    ExcludeConfig,
    FiltersConfig,
    IncludeConfig,
    SpotifyConfig,
    SpotiSyncConfig,
    SyncGroupConfig,
)


class TestSpotifyConfig:
    def test_default_redirect_uri(self) -> None:
        config = SpotifyConfig(client_id="test_id", client_secret="test_secret")

        assert config.redirect_uri == "https://example.com/callback"

    def test_custom_redirect_uri(self) -> None:
        config = SpotifyConfig(
            client_id="test_id",
            client_secret="test_secret",
            redirect_uri="https://example.com/callback",
        )

        assert config.redirect_uri == "https://example.com/callback"

    def test_invalid_redirect_uri_raises_error(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SpotifyConfig(
                client_id="test_id",
                client_secret="test_secret",
                redirect_uri="invalid-uri",
            )

        assert "redirect_uri must start with http://" in str(exc_info.value)

    def test_default_scopes(self) -> None:
        config = SpotifyConfig(client_id="test_id", client_secret="test_secret")

        assert "user-library-read" in config.scopes
        assert "playlist-modify-private" in config.scopes
        assert len(config.scopes) == 4


class TestFiltersConfig:
    def test_default_values(self) -> None:
        config = FiltersConfig()

        assert config.skip_podcasts is True
        assert config.include.artists == []
        assert config.exclude.artists == []
        assert config.exclude.albums == []
        assert config.exclude.tracks == []


class TestIncludeConfig:
    def test_default_empty_list(self) -> None:
        config = IncludeConfig()

        assert config.artists == []

    def test_with_artists(self) -> None:
        config = IncludeConfig(artists=["4Z8W4fKeB5YxbusRsdQVPb", "(?i)radiohead"])

        assert len(config.artists) == 2


class TestExcludeConfig:
    def test_default_empty_lists(self) -> None:
        config = ExcludeConfig()

        assert config.artists == []
        assert config.albums == []
        assert config.tracks == []

    def test_with_patterns(self) -> None:
        config = ExcludeConfig(
            artists=["0OdUWJ0sBjDrqHygGUXeCF", "(?i)christmas"],
            albums=["album123"],
            tracks=["(?i)remix"],
        )

        assert len(config.artists) == 2
        assert len(config.albums) == 1
        assert len(config.tracks) == 1


class TestFiltersConfigValidation:
    def test_overlapping_artists_raises_error(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            FiltersConfig(
                include=IncludeConfig(artists=["4Z8W4fKeB5YxbusRsdQVPb"]),
                exclude=ExcludeConfig(artists=["4Z8W4fKeB5YxbusRsdQVPb"]),
            )

        assert "cannot appear in both include and exclude" in str(exc_info.value)

    def test_different_artists_allowed(self) -> None:
        config = FiltersConfig(
            include=IncludeConfig(artists=["4Z8W4fKeB5YxbusRsdQVPb"]),
            exclude=ExcludeConfig(artists=["0OdUWJ0sBjDrqHygGUXeCF"]),
        )

        assert len(config.include.artists) == 1
        assert len(config.exclude.artists) == 1


class TestCronConfig:
    def test_valid_cron_expression(self) -> None:
        config = CronConfig(schedule="0 * * * *")
        assert config.schedule == "0 * * * *"

        config = CronConfig(schedule="*/15 * * * *")
        assert config.schedule == "*/15 * * * *"

    def test_invalid_cron_expression_raises_error(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            CronConfig(schedule="invalid")

        assert "Invalid cron expression" in str(exc_info.value)

        with pytest.raises(ValidationError):
            CronConfig(schedule="* * *")

    def test_default_values(self) -> None:
        config = CronConfig()

        assert config.enabled is False
        assert config.schedule == "*/10 * * * *"


class TestSyncGroupConfig:
    def test_valid_liked_tracks_source(self) -> None:
        config = SyncGroupConfig(
            name="test",
            source="liked_tracks",
            target="1234567890abcdefghijkl",
        )

        assert config.source == "liked_tracks"

    def test_valid_playlist_id_source(self) -> None:
        config = SyncGroupConfig(
            name="test",
            source="1234567890abcdefghijkl",
            target="abcdefghijkl1234567890",
        )

        assert config.source == "1234567890abcdefghijkl"

    def test_invalid_source_raises_error(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SyncGroupConfig(
                name="test",
                source="invalid",
                target="1234567890abcdefghijkl",
            )

        assert "Invalid source" in str(exc_info.value)

    def test_valid_target_playlist_id(self) -> None:
        config = SyncGroupConfig(
            name="test",
            source="liked_tracks",
            target="1234567890abcdefghijkl",
        )

        assert config.target == "1234567890abcdefghijkl"

    def test_invalid_target_raises_error(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SyncGroupConfig(
                name="test",
                source="liked_tracks",
                target="short",
            )

        assert "Invalid target playlist ID" in str(exc_info.value)

    def test_spotify_uri_normalized(self) -> None:
        config = SyncGroupConfig(
            name="test",
            source="spotify:playlist:1234567890abcdefghijkl",
            target="spotify:playlist:abcdefghijkl1234567890",
        )

        assert config.source == "1234567890abcdefghijkl"
        assert config.target == "abcdefghijkl1234567890"

    def test_skip_removals_default_false(self) -> None:
        config = SyncGroupConfig(
            name="test",
            source="liked_tracks",
            target="1234567890abcdefghijkl",
        )

        assert config.skip_removals is False

    def test_skip_removals_can_be_enabled(self) -> None:
        config = SyncGroupConfig(
            name="test",
            source="liked_tracks",
            target="1234567890abcdefghijkl",
            skip_removals=True,
        )

        assert config.skip_removals is True

    def test_valid_kebab_case_names(self) -> None:
        valid_names = ["my-sync", "daily-liked-sync-2", "a", "sync123", "my-sync-group"]
        for name in valid_names:
            config = SyncGroupConfig(
                name=name,
                source="liked_tracks",
                target="1234567890abcdefghijkl",
            )
            assert config.name == name

    def test_invalid_name_special_chars(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SyncGroupConfig(
                name="my-sync/$@#",
                source="liked_tracks",
                target="1234567890abcdefghijkl",
            )
        assert "Must be kebab-case" in str(exc_info.value)

    def test_invalid_name_uppercase(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SyncGroupConfig(
                name="My-Sync",
                source="liked_tracks",
                target="1234567890abcdefghijkl",
            )
        assert "Must be kebab-case" in str(exc_info.value)

    def test_invalid_name_too_long(self) -> None:
        with pytest.raises(ValidationError):
            SyncGroupConfig(
                name="a" * 51,
                source="liked_tracks",
                target="1234567890abcdefghijkl",
            )

    def test_invalid_name_starts_with_hyphen(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SyncGroupConfig(
                name="-my-sync",
                source="liked_tracks",
                target="1234567890abcdefghijkl",
            )
        assert "Must be kebab-case" in str(exc_info.value)

    def test_invalid_name_ends_with_hyphen(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SyncGroupConfig(
                name="my-sync-",
                source="liked_tracks",
                target="1234567890abcdefghijkl",
            )
        assert "Must be kebab-case" in str(exc_info.value)


class TestSpotiSyncConfig:
    def test_minimal_valid_config(self) -> None:
        config = SpotiSyncConfig(
            spotify=SpotifyConfig(client_id="id", client_secret="secret"),
            sync_groups=[
                SyncGroupConfig(
                    name="main",
                    source="liked_tracks",
                    target="1234567890abcdefghijkl",
                )
            ],
        )

        assert len(config.sync_groups) == 1
        assert config.filters.skip_podcasts is True
        assert config.cron.enabled is False

    def test_duplicate_sync_group_names_raises_error(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SpotiSyncConfig(
                spotify=SpotifyConfig(client_id="id", client_secret="secret"),
                sync_groups=[
                    SyncGroupConfig(
                        name="duplicate",
                        source="liked_tracks",
                        target="1234567890abcdefghijkl",
                    ),
                    SyncGroupConfig(
                        name="duplicate",
                        source="liked_tracks",
                        target="abcdefghijkl1234567890",
                    ),
                ],
            )

        assert "Duplicate sync group names" in str(exc_info.value)

    def test_get_enabled_sync_groups(self) -> None:
        config = SpotiSyncConfig(
            spotify=SpotifyConfig(client_id="id", client_secret="secret"),
            sync_groups=[
                SyncGroupConfig(
                    name="enabled1",
                    source="liked_tracks",
                    target="1234567890abcdefghijkl",
                ),
                SyncGroupConfig(
                    name="disabled1",
                    source="liked_tracks",
                    target="abcdefghijkl1234567890",
                    disabled=True,
                ),
                SyncGroupConfig(
                    name="enabled2",
                    source="liked_tracks",
                    target="klmnopqrst1234567890ab",
                ),
            ],
        )

        enabled = config.get_enabled_sync_groups()

        assert len(enabled) == 2
        assert all(not g.disabled for g in enabled)
        assert enabled[0].name == "enabled1"
        assert enabled[1].name == "enabled2"

    def test_empty_sync_groups_raises_error(self) -> None:
        with pytest.raises(ValidationError):
            SpotiSyncConfig(
                spotify=SpotifyConfig(client_id="id", client_secret="secret"),
                sync_groups=[],
            )
