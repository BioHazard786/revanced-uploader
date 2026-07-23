"""Async GitHub API client for fetching releases and downloading assets."""

from __future__ import annotations

from pathlib import Path

import httpx
import structlog

from revanced_bot.config import Settings
from revanced_bot.models import Release, ReleaseAsset

log = structlog.get_logger()


class GitHubClient:
    """Thin async wrapper around the GitHub REST API (releases endpoint)."""

    _API_BASE = "https://api.github.com"

    def __init__(self, settings: Settings) -> None:
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        self._client = httpx.AsyncClient(
            headers=headers,
            timeout=httpx.Timeout(30.0, read=120.0),
            follow_redirects=True,
        )
        self._repo = settings.github_repo
        self._download_dir = settings.download_dir

    # ── release fetching ──────────────────────────────────────

    async def get_latest_release(self) -> Release:
        """Fetch the latest release from GitHub."""
        url = f"{self._API_BASE}/repos/{self._repo}/releases/latest"
        resp = await self._client.get(url)

        match resp.status_code:
            case 200:
                pass
            case 403:
                remaining = resp.headers.get("x-ratelimit-remaining", "?")
                log.warning("github_rate_limited", remaining=remaining)
                resp.raise_for_status()
            case _:
                resp.raise_for_status()

        data = resp.json()
        assets = [
            ReleaseAsset(
                name=a["name"],
                size=a["size"],
                download_url=a["browser_download_url"],
            )
            for a in data["assets"]
        ]
        return Release(
            tag_name=data["tag_name"],
            published_at=data["published_at"],
            html_url=data["html_url"],
            assets=assets,
        )

    @staticmethod
    def filter_apk_assets(release: Release) -> list[ReleaseAsset]:
        """Keep only *.apk* files, drop Magisk *.zip* modules."""
        return [a for a in release.assets if a.name.endswith(".apk")]

    # ── asset download ────────────────────────────────────────

    async def download_asset(self, asset: ReleaseAsset) -> Path:
        """Stream-download an asset to a temp file and return its path."""
        self._download_dir.mkdir(parents=True, exist_ok=True)
        dest = self._download_dir / asset.name
        size_mb = asset.size / (1024 * 1024)

        log.info("download_start", asset=asset.name, size_mb=f"{size_mb:.1f}")

        async with self._client.stream("GET", asset.download_url) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            last_logged_pct = -25

            with dest.open("wb") as fh:
                async for chunk in resp.aiter_bytes(chunk_size=65_536):
                    fh.write(chunk)
                    downloaded += len(chunk)

                    if total:
                        pct = int(downloaded * 100 / total)
                        if pct - last_logged_pct >= 25:
                            last_logged_pct = pct
                            log.debug(
                                "download_progress",
                                asset=asset.name,
                                pct=f"{pct}%",
                            )

        log.info("download_complete", asset=asset.name, path=str(dest))
        return dest

    # ── lifecycle ─────────────────────────────────────────────

    async def close(self) -> None:
        await self._client.aclose()
