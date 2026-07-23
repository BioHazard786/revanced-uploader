# ReVanced Releases → Telegram Channel Bot

Automatically monitors [j-hc/revanced-magisk-module](https://github.com/j-hc/revanced-magisk-module/releases) for new releases, filters only `.apk` files (skips Magisk `.zip` modules), and uploads them to your Telegram channel.

## Stack

| Component | Tech |
|-----------|------|
| Telegram client | [kurigram](https://github.com/KurimuzonAkuma/kurigram) (pyrogram fork) |
| HTTP client | httpx (async, streaming downloads) |
| Config | pydantic-settings (`.env` → typed Python) |
| Event loop | uvloop |
| Logging | structlog |
| Packaging | uv (local dev) / pip (Docker) |
| Runtime | Docker Compose on Alpine |

## Architecture

```
Poller ──▶ asyncio.Queue[UploadTask] ──▶ Worker(s)
                                         ├─ download (httpx stream)
                                         └─ upload   (kurigram send_document)
```

- **Poller** checks GitHub every N seconds, enqueues new APKs
- **Workers** (default 2) pull tasks, download, upload, clean up
- **State** is persisted to `data/state.json` — survives restarts
- **Shutdown watcher** listens for `SIGINT` / `SIGTERM` and drains gracefully

## Setup

### 1. Get credentials

| What | Where |
|------|-------|
| `API_ID` + `API_HASH` | [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) |
| `CHANNEL_ID` | Numeric ID or `@username` (bot must be **admin**) |
| `GITHUB_TOKEN` *(optional)* | [GitHub PAT](https://github.com/settings/tokens) with `public_repo` scope |

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Run with Docker Compose

```bash
docker compose up -d
docker compose logs -f
```

### 4. Run locally (dev)

```bash
# Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv and install
uv sync

# Run
uv run python -m revanced_bot
```

## Configuration

All options are set via environment variables or `.env`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_ID` | ✅ | — | Telegram API ID |
| `API_HASH` | ✅ | — | Telegram API hash |
| `BOT_TOKEN` | ✅ | — | Bot token from BotFather |
| `CHANNEL_ID` | ✅ | — | Target channel ID or @username |
| `GITHUB_TOKEN` | ❌ | `None` | GitHub PAT (raises rate limit to 5k/hr) |
| `POLL_INTERVAL` | ❌ | `600` | Seconds between GitHub checks |
| `NUM_WORKERS` | ❌ | `2` | Concurrent upload workers |
| `GITHUB_REPO` | ❌ | `j-hc/revanced-magisk-module` | Repository to monitor |

## License

MIT
