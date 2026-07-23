"""Telegram service — upload APKs to a channel via kurigram (pyrogram fork)."""

from __future__ import annotations

import re
from pathlib import Path

import structlog
from pyrogram import Client  # kurigram is a drop-in pyrogram replacement

from revanced_bot.config import Settings
from revanced_bot.models import ReleaseAsset

log = structlog.get_logger()

# ── helpers ───────────────────────────────────────────────────

type AppInfo = tuple[str, str, str]  # (app_name, version, arch)

# Arch can be multi-segment (arm64-v8a, arm-v7a) so we anchor it explicitly.
_FILENAME_RE = re.compile(
    r"^(.+)-morphe-v([\d.]+)-([\w-]+)\.apk$",
)
_KNOWN_ARCHS = {"arm64-v8a", "arm-v7a", "armeabi-v7a", "x86", "x86_64", "all"}


def _split_version_arch(version_arch: str) -> tuple[str, str]:
    """Handle filenames where version and arch share hyphen-delimited segments.

    e.g. ``9.15.51-arm64-v8a`` → ``('9.15.51', 'arm64-v8a')``
    """
    # Try known arch suffixes from longest to shortest
    for arch in sorted(_KNOWN_ARCHS, key=len, reverse=True):
        if version_arch.endswith(arch):
            ver = version_arch[: -(len(arch) + 1)]  # strip '-{arch}'
            if ver:
                return ver, arch
    return version_arch, "unknown"


_APP_EMOJI: dict[str, str] = {
    "youtube": "▶️",
    "music": "🎵",
    "reddit": "🤖",
    "twitter": "🐦",
    "tiktok": "🎶",
}


def _parse_apk_name(filename: str) -> AppInfo:
    """Extract app name, version, and architecture from the APK filename."""
    if m := _FILENAME_RE.match(filename):
        return m.group(1).replace("-", " ").title(), m.group(2), m.group(3)
    # Fallback for unexpected naming schemes
    stem = Path(filename).stem
    return stem, "unknown", "unknown"


def _build_caption(asset: ReleaseAsset, release_tag: str) -> str:
    name, version, arch = _parse_apk_name(asset.name)
    emoji = _APP_EMOJI.get(name.split()[0].lower(), "📦")
    size_mb = asset.size / (1024 * 1024)
    return (
        f"{emoji} **{name} ReVanced**\n"
        f"📌 Version: `v{version}`\n"
        f"🏗️ Arch: `{arch}`\n"
        f"🏷️ Tag: `{release_tag}`\n"
        f"📏 Size: `{size_mb:.1f} MB`"
    )


# ── service ───────────────────────────────────────────────────


class TelegramService:
    """Wraps a kurigram Client for uploading documents to a channel."""

    def __init__(self, settings: Settings) -> None:
        workdir = Path("data")
        workdir.mkdir(parents=True, exist_ok=True)

        self._client = Client(
            name="revanced_bot",
            api_id=settings.api_id,
            api_hash=settings.api_hash,
            bot_token=settings.bot_token,
            workdir=str(workdir),
        )
        self._channel_id = settings.channel_id

    async def start(self) -> None:
        await self._client.start()
        me = await self._client.get_me()
        log.info("telegram_connected", bot=me.username)

    async def stop(self) -> None:
        if self._client.is_connected:
            await self._client.stop(block=False)
            log.info("telegram_disconnected")

    async def upload_apk(
        self,
        file_path: Path,
        asset: ReleaseAsset,
        release_tag: str,
    ) -> None:
        """Upload a single APK to the configured channel."""
        caption = _build_caption(asset, release_tag)
        log.info("upload_start", asset=asset.name, channel=self._channel_id)

        last_logged_pct = -25

        async def _progress(current: int, total: int) -> None:
            nonlocal last_logged_pct
            if total == 0:
                return
            pct = int(current * 100 / total)
            if pct - last_logged_pct >= 25:
                last_logged_pct = pct
                log.debug("upload_progress", asset=asset.name, pct=f"{pct}%")

        await self._client.send_document(
            chat_id=self._channel_id,
            document=str(file_path),
            caption=caption,
            progress=_progress,
            force_document=True,
        )

        log.info("upload_complete", asset=asset.name)
