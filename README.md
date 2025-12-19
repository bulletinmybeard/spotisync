# SpotiSync

[![CI](https://github.com/bulletinmybeard/spotisync/actions/workflows/ci.yml/badge.svg)](https://github.com/bulletinmybeard/spotisync/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/spotisync.svg)](https://pypi.org/project/spotisync/)
[![Python Versions](https://img.shields.io/pypi/pyversions/spotisync.svg)](https://pypi.org/project/spotisync/)
[![Poetry](https://img.shields.io/badge/poetry-managed-blue.svg)](https://python-poetry.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Type checking: mypy](https://img.shields.io/badge/type%20checking-mypy-blue.svg)](https://github.com/python/mypy)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Automatically sync tracks between playlists - from your Liked Songs, your own playlists, or any public playlist on Spotify.

Want to share your liked tracks as a public playlist? Create a backup that never loses tracks? Mirror someone else's playlist to your own? SpotiSync handles it all.

## What It Does

- Sync your Liked Songs to any playlist you own
- Use any public Spotify playlist as a source (even ones you don't own!)
- Sync between your own playlists
- Archive mode: keep tracks even after their removal from the source playlist (`skip_removals`)
- Filter out local files, podcasts, and specific tracks
- Create artist-specific playlists with include filters
- Preview changes before applying (`dry-run` mode)
- Run on a schedule with Docker

## Quick Start

### Create a Spotify Developer App

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
1. Click **Create app**
1. Set Redirect URI to `https://example.com/callback`
   > This is the default. If you change it, update `spotify.redirect_uri` in your config to match exactly.
1. Note down the App's **Client ID** and **Client Secret**

**Required scopes** (configured automatically):

- `user-library-read` - Read your Liked Songs
- `playlist-read-private` - Read private playlists
- `playlist-modify-public` / `playlist-modify-private` - Modify playlists

### Install SpotiSync

Install SpotiSync with `pipx` to run it as a standalone tool without affecting your system Python:

```bash
pipx install spotisync
```

Or with pip in a virtual environment:

```bash
pip install spotisync
```

> **Note:** I recommend `pipx` for global CLI installation!

Or with Poetry (for development):

```bash
git clone https://github.com/bulletinmybeard/spotisync.git
cd spotisync
poetry install
```

### Run the Setup Wizard

```bash
spotisync init
```

This guides you through:

- Entering your Spotify credentials
- Choosing a source (Liked Songs or a playlist)
- Selecting a target playlist
- Configuring filters (optional)

### Authenticate

```bash
spotisync auth
```

A browser window opens to authorize SpotiSync with your Spotify account.

### Sync

```bash
# Preview what will change
spotisync sync --dry-run

# Run the sync
spotisync sync
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `spotisync init` | Interactive setup wizard |
| `spotisync init -o PATH` | Setup with custom config output path |
| `spotisync auth` | Authenticate with Spotify |
| `spotisync auth --clear` | Clear stored authentication token |
| `spotisync sync` | Run all enabled sync groups |
| `spotisync sync --dry-run` | Preview changes without applying |
| `spotisync sync -n NAME` | Sync specific group(s) by name |
| `spotisync sync --json` | JSON output for automation |
| `spotisync status` | Show auth and config status |
| `spotisync status --json` | JSON output |
| `spotisync config` | Display current configuration (YAML) |
| `spotisync config --json` | Display as JSON |
| `spotisync add` | Add a new sync group (wizard) |

**Global option:** `--config/-c PATH` to override config file location.

## Automation

SpotiSync supports JSON output for scripting and CI/CD:

```bash
# Check sync results programmatically
spotisync sync --json | jq '.summary'

# Sync specific groups with JSON output
spotisync sync -n "daily-backup" -n "discover-weekly" --json

# Get authentication status
spotisync status --json | jq '.authentication.authenticated'
```

Exit codes: `0` on success, `1` on error.

## Configuration

SpotiSync uses a `config.yaml` file. The setup wizard creates this for you, or see [`config.example.yaml`](https://github.com/bulletinmybeard/spotisync/blob/master/config.example.yaml) for all options.

**Multiple sync groups** - Sync different sources to different targets:

```yaml
sync_groups:
  - name: liked-to-public
    source: liked_tracks
    target: 3cEYpjA9oz9GiPac4AsH4n

  - name: discover-backup
    source: 37i9dQZEVXcQ9COmYvdajy  # Any public playlist (e.g., Spotify's Discover Weekly)
    target: 5Rrf7mqN8uus2AaQQQNdc1
```

**Config file locations** (checked in order):

1. Docker: `/app/config.yaml`
1. Development (git repo): `./config.yaml`
1. User home: `~/.spotisync/config.yaml`

Override with `--config/-c PATH` on any command.

> **How to get a playlist ID:** Open the playlist in Spotify, click Share → Copy link.
> The ID is the string after `/playlist/`: `https://open.spotify.com/playlist/37i9dQZEVXcQ9COmYvdajy` → `37i9dQZEVXcQ9COmYvdajy`

## Filtering

SpotiSync supports multiple different filter options to dictate which tracks should be included or excluded from the sync.

### Examples

**Include filters** - Create artist-specific playlists from Liked Songs:

```yaml
sync_groups:
  - name: eddie-unchained
    source: liked_tracks
    target: 3cEYpjA9oz9GiPac4AsH4n   # Your target playlist ID
    filters:
      include:
        artists:
          - 6mdiAmATAx73kdxrNrnlao # Iron Maiden
```

**Include filters** - Filter a public playlist to specific artists:

```yaml
sync_groups:
  - name: doom-eternal-uncluttered
    source: 6s4aGjq9b42OP4nMGNCLUu   # DOOM Eternal soundtrack (public playlist)
    target: 9pXbKfV5dQ3sLz2nTj1uRw   # Your custom playlist
    filters:
      include:
        artists:
          - 13ab1LgQZ3tQOhkDRRYB8Y   # Mick Gordon
```

**Exclude filters** - Skip unwanted tracks:

```yaml
sync_groups:
  - name: no-remasters
    source: 6vr1Nnese49l0hxQEljOQn # Your source playlist ID
    target: 3cEYojA9oz9hiPac4AsH4n # Your target playlist ID
    filters:
      exclude:
        tracks:
          - '(?i)\bremaster(?:ed)?(?:\s+\d{4})?\b' # e.g., Metallica / Enter Sandman - Remastered 2021
```

**Combined filters** - Use both include and exclude:

```yaml
filters:
  exclude:
    artists:
      - '(?i)christmas' # Regex patterns
    albums:
      - 0sNOF9WDwhWunNAHPD3Baj # Spotify IDs
    tracks:
      - '(?i)remix'
      - '(?i)live'
```

**Other filters:**

- `skip_podcasts: true` - Skip podcast episodes (default)

Include filters are applied before exclude filters, so you can create an artist playlist and still exclude particular tracks.

**Filter inheritance:** Per-group filters merge with root filters:

- `skip_podcasts`: Per-group value overrides root
- `include`/`exclude` lists: Combined (both root and group patterns apply)

## Archive Mode

Want a backup playlist that never loses tracks? Use `skip_removals` to keep tracks in the target even after removing them from the source:

```yaml
sync_groups:
  - name: liked-tracks-archive
    source: liked_tracks
    target: 3cEYpjA9oz9GiPac4AsH4n # Your target playlist ID
    skip_removals: true  # Tracks removed from the source stay in the target playlist
```

This is useful for:

- Backup playlists that hold all tracks you've ever liked
- Preserving a history of tracks from a dynamic source playlist

## Using Regex for Track Filtering

Spotify tracks often include version markers in their titles like "(Live)", "- Remastered 2021", or "(Acoustic)". Regular expressions (regex) let you match these patterns flexibly to include or exclude specific track versions.

<details>
<summary><b>Regex Basics & Common Patterns</b></summary>

### Regex Basics

The patterns below use these common regex features:

| Syntax | Meaning | Example |
|--------|---------|---------|
| `(?i)` | Case-insensitive | `(?i)live` matches "Live", "LIVE", "live" |
| `\b` | Word boundary | `\blive\b` matches "Live" but not "Oliver" |
| `(a\|b)` | Either a or b | `(remix\|live)` matches either |
| `?` | Optional | `remaster(ed)?` matches "remaster" or "remastered" |
| `\d{4}` | Four digits | Matches years like "2021" |

> **YAML tip:** Use single quotes around patterns to avoid escaping backslashes.

### Common Patterns

| Pattern | Matches | Example Track Title |
|---------|---------|---------------------|
| `'(?i)\bremaster(ed)?(\s+\d{4})?\b'` | Remastered versions | "Enter Sandman - Remastered 2021" |
| `'(?i)\blive\b'` | Live recordings | "Nothing Else Matters (Live)" |
| `'(?i)acoustic'` | Acoustic versions | "Layla (Acoustic)" |
| `'(?i)remix'` | Remixes | "Blinding Lights (Remix)" |
| `'(?i)\bdemo\b'` | Demo recordings | "Bohemian Rhapsody (Demo)" |
| `'(?i)instrumental'` | Instrumentals | "Stairway to Heaven (Instrumental)" |
| `'(?i)radio edit'` | Radio edits | "Purple Haze - Radio Edit" |
| `'(?i)(deluxe\|bonus)'` | Deluxe/bonus tracks | "Album Name (Deluxe Edition)" |
| `'(?i)(feat\.\|ft\.\|featuring)'` | Featuring artists | "Song (feat. Artist)" |

</details>

## Docker

This repo includes `docker-compose.yml` for scheduled syncing.

```bash
# Start the container (runs cron daemon)
docker compose up -d

# Run a manual sync
docker exec spotisync spotisync sync

# Check status
docker exec spotisync spotisync status
```

**Volume mounts required:**

- `./config.yaml:/app/config.yaml` - Your configuration
- `./tokens.json:/app/tokens.json` - Auth tokens (created after `spotisync auth`)

Configure the schedule in `config.yaml`:

```yaml
cron:
  enabled: true
  schedule: "0 * * * *"  # Every hour
```

> **Note:** Container name is `spotisync` - matches the shell wrapper functions below.

## Shell Integration (Development Only)

> **Note:** This section is only relevant if you run SpotiSync from the cloned repo via `poetry run`. If you installed it via `pip` or `pipx`, just use `spotisync` directly.

These optional wrapper functions provide a convenient `spotisync` shortcut when running from a cloned repo.

<details>
<summary><b>Linux/macOS (ZSH/Bash)</b></summary>

Create `~/spotisync_shell.sh`:

**For Poetry:**

```bash
spotisync() {
    local project_dir="$HOME/path/to/spotisync"
    if [[ ! -d "$project_dir" ]]; then
        echo "Error: spotisync project not found at $project_dir"
        return 1
    fi
    (cd "$project_dir" && poetry run spotisync "$@")
}
```

**For Docker:**

```bash
spotisync() {
    if ! docker ps --format '{{.Names}}' | grep -q 'spotisync'; then
        echo "Error: spotisync container is not running"
        return 1
    fi
    docker exec -it spotisync spotisync "$@"
}
```

Then add to `~/.zshrc` or `~/.bashrc`:

```bash
[ -f "$HOME/spotisync_shell.sh" ] && source "$HOME/spotisync_shell.sh"
```

Reload: `source ~/.zshrc`

</details>

<details>
<summary><b>Windows (PowerShell)</b></summary>

Create `~\spotisync_shell.ps1`:

**For Poetry:**

```powershell
function spotisync {
    $projectDir = "$env:USERPROFILE\path\to\spotisync"
    if (-not (Test-Path $projectDir)) {
        Write-Error "spotisync project not found at $projectDir"
        return
    }
    Push-Location $projectDir
    try { poetry run spotisync @args }
    finally { Pop-Location }
}
```

**For Docker:**

```powershell
function spotisync {
    $running = docker ps --format '{{.Names}}' | Select-String -Quiet 'spotisync'
    if (-not $running) {
        Write-Error "spotisync container is not running"
        return
    }
    docker exec -it spotisync spotisync @args
}
```

Then add to your PowerShell profile (`$PROFILE`):

```powershell
if (Test-Path "$env:USERPROFILE\spotisync_shell.ps1") { . "$env:USERPROFILE\spotisync_shell.ps1" }
```

Reload: `. $PROFILE`

</details>

## Requirements

- Spotify account
- Spotify Developer App credentials
- Python 3.12+

## Links

- [Configuration Example](https://github.com/bulletinmybeard/spotisync/blob/master/config.example.yaml)
- [Changelog](https://github.com/bulletinmybeard/spotisync/blob/master/CHANGELOG.md)

## License

MIT License - see the [LICENSE](https://github.com/bulletinmybeard/spotisync/blob/master/LICENSE) file for details.
