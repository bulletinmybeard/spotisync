import json
import os
from pathlib import Path
import shutil
from typing import Any

from pydantic import ValidationError
import yaml

from src.config.models import (
    ExcludeConfig,
    FiltersConfig,
    IncludeConfig,
    SpotiSyncConfig,
    SyncGroupConfig,
)

USER_DIRECTORY_NAME = ".spotisync"


class ConfigValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        message = "; ".join(errors)
        super().__init__(message)

    def formatted_message(self) -> str:
        if len(self.errors) == 1:
            return self.errors[0]
        return "\n".join(f"  - {err}" for err in self.errors)


def is_docker_environment() -> bool:
    return os.getenv("IN_DOCKER") == "1" or Path("/.dockerenv").exists()


def is_development_environment() -> bool:
    if is_docker_environment():
        return False

    try:
        current = Path.cwd()
        while current != current.parent:
            git_dir = current / ".git"
            pyproject = current / "pyproject.toml"

            if git_dir.exists() and pyproject.exists():
                return True

            current = current.parent

        return False
    except Exception:
        return False


def get_user_directory() -> Path:
    return Path.home() / USER_DIRECTORY_NAME


def get_data_directory() -> Path:
    if is_docker_environment():
        return Path("/app")
    if is_development_environment():
        return Path(__file__).parent.parent.parent
    return get_user_directory()


def get_token_path() -> Path:
    return get_data_directory() / "tokens.json"


def ensure_user_directory() -> bool:
    if is_development_environment():
        return True

    user_dir = get_user_directory()
    config_file = user_dir / "config.yaml"

    try:
        user_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False

    if not config_file.exists():
        bundled_example = Path(__file__).parent.parent.parent / "config.example.yaml"

        if bundled_example.exists():
            try:
                shutil.copy(bundled_example, config_file)
            except OSError:
                return False

    return True


def get_default_config_path() -> Path:
    if not is_docker_environment() and not is_development_environment():
        ensure_user_directory()
    return get_data_directory() / "config.yaml"


class ConfigLoader:
    def __init__(self, config_path: str | Path | None = None) -> None:
        if config_path is None:
            config_path = get_default_config_path()

        self.config_path = Path(config_path)
        self.config: dict[str, Any] = {}
        self._pydantic_config: SpotiSyncConfig | None = None

    @staticmethod
    def _find_bundled_example() -> Path | None:
        candidates = [
            Path("/app/config.example.yaml"),
            Path(__file__).parent.parent.parent / "config.example.yaml",
            Path(__file__).parent.parent / "config.example.yaml",
            Path.cwd() / "config.example.yaml",
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return None

    def _create_default_config(self) -> bool:
        bundled_example = self._find_bundled_example()

        if not bundled_example:
            return False

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(bundled_example, self.config_path)
            return True

        except OSError:
            return False

    def load(self) -> dict[str, Any]:
        if not self.config_path.exists():
            if self._create_default_config():
                print(f"Created default config at: {self.config_path}")
                print("Please update with your Spotify API credentials and playlist IDs")
            else:
                raise FileNotFoundError(
                    f"Config file not found: {self.config_path}\n"
                    f"Could not find bundled config.example.yaml to create default config.\n"
                    f"Please create config manually or run: spotisync config init"
                )

        try:
            with open(self.config_path, encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}

            return self.config

        except yaml.YAMLError as e:
            print(f"Failed to parse {self.config_path.name}: {e}")
            raise

    def load_typed(self) -> SpotiSyncConfig:
        if not self.config:
            self.load()

        try:
            self._pydantic_config = SpotiSyncConfig(**self.config)
            return self._pydantic_config

        except ValidationError as e:
            errors = []
            for err in e.errors():
                msg = err["msg"]
                if msg.startswith("Value error, "):
                    msg = msg[13:]
                errors.append(msg)
            raise ConfigValidationError(errors) from None

    def to_json(self) -> str:
        return json.dumps(self.config, indent=2)

    def __repr__(self) -> str:
        return f"ConfigLoader(config_path={self.config_path})"


def load_typed_config(config_path: str | Path | None = None) -> SpotiSyncConfig:
    loader = ConfigLoader(config_path)
    return loader.load_typed()


def merge_include_config(root: IncludeConfig, override: IncludeConfig) -> IncludeConfig:
    return IncludeConfig(
        artists=list(set(root.artists + override.artists)),
        tracks=list(set(root.tracks + override.tracks)),
    )


def merge_exclude_config(root: ExcludeConfig, override: ExcludeConfig) -> ExcludeConfig:
    return ExcludeConfig(
        artists=list(set(root.artists + override.artists)),
        albums=list(set(root.albums + override.albums)),
        tracks=list(set(root.tracks + override.tracks)),
    )


def merge_filters(root: FiltersConfig, override: FiltersConfig | None) -> FiltersConfig:
    if override is None:
        return root

    merged_include = merge_include_config(root.include, override.include)
    merged_exclude = merge_exclude_config(root.exclude, override.exclude)

    return FiltersConfig(
        skip_podcasts=override.skip_podcasts,
        include=merged_include,
        exclude=merged_exclude,
    )


def get_effective_filters(config: SpotiSyncConfig, sync_group: SyncGroupConfig) -> FiltersConfig:
    return merge_filters(config.filters, sync_group.filters)
