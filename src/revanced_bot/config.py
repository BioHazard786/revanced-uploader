"""Application configuration via pydantic-settings."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration is read from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Telegram ──────────────────────────────────────────────
    api_id: int
    api_hash: str
    bot_token: str
    channel_id: int

    # ── GitHub ────────────────────────────────────────────────
    github_token: str | None = None
    github_repo: str = "j-hc/revanced-magisk-module"

    # ── Tuning ────────────────────────────────────────────────
    poll_interval: int = 600  # seconds (10 minutes)
    num_workers: int = 2
    download_dir: Path = Path("downloads")
    state_file: Path = Path("data/state.json")
