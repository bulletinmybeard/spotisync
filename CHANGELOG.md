# Changelog

All notable changes to SpotiSync will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.2] - 2025-12-19

### Fixed

- Fixed relative links in README that didn't work on PyPI

## [0.1.1] - 2025-12-19

### Added

#### Core Features

- Spotify OAuth authentication with token refresh
- Sync liked tracks to any playlist (public or private)
- Sync playlist to playlist
- Diff-based incremental sync mode that preserves the existing track order
- Dry-run mode to preview sync changes before applying them

#### CLI Commands

- `spotisync auth` - Authenticate with Spotify
  - Automatic browser opening for authorization URL
  - `--clear` option to remove existing tokens
  - Displays user info and token expiry after successful authentication
- `spotisync sync` - Run sync operation
  - `--dry-run` flag to preview changes without applying
  - Supports single group or all groups
- `spotisync status` - Show configuration and authentication status
  - Token expiry display with hours and minutes
  - Refresh token status indicator
- `spotisync config` - Validate and display configuration
  - YAML format (default) or JSON with `--format json`
- `spotisync init` - Interactive setup wizard
  - Guides through complete SpotiSync configuration
  - Spotify Developer App setup instructions
  - Credential collection with validation
  - Source selection (Liked Songs or playlist)
  - Target playlist selection
  - Filter and sync behavior configuration
  - Automatic config.yaml generation
- `spotisync add` - Add new sync group interactively

#### Filter Engine

- Skip local files (always enabled)
- Skip podcast episodes (configurable)
- Include specific artists (allowlist by Spotify ID or regex pattern)
- Exclude specific artists (by Spotify ID or regex pattern)
- Exclude specific albums (by Spotify ID or regex pattern)
- Exclude tracks by name (regex pattern matching)
- Include filters applied before exclude filters for combined filtering

#### Configuration

- YAML-based configuration with Pydantic v2 validation
- Multiple sync groups support (source -> target mappings)
- Per-group filter overrides
- Per-group cron schedule overrides

#### Docker Support

- Docker Compose support
- Cron scheduling inside containers
- Automatic config creation from example template
