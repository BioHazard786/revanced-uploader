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
_KNOWN_PATCHERS = {"morphe", "piko", "devanced", "revanced"}
_KNOWN_ARCHS = {
    "arm64-v8a",
    "arm-v7a",
    "armeabi-v7a",
    "armeabi",
    "arm64",
    "arm",
    "x86_64",
    "x86",
    "x64",
    "universal",
    "all",
}

_APP_DISPLAY_NAMES: dict[str, str] = {
    "googlephotos": "Google Photos",
    "google-photos": "Google Photos",
    "youtube": "YouTube",
    "youtube-music": "YouTube Music",
    "music": "Music",
    "reddit": "Reddit",
    "twitter": "Twitter",
    "tiktok": "TikTok",
    "twitch": "Twitch",
}

_APP_EMOJI: dict[str, str] = {
    "youtube": "▶️",
    "music": "🎵",
    "reddit": "🤖",
    "twitter": "🐦",
    "tiktok": "🎶",
    "google photos": "📷",
    "googlephotos": "📷",
    "google": "📷",
    "photos": "📷",
    "twitch": "🟣",
}

_ARCH_PATTERN = "|".join(sorted(_KNOWN_ARCHS, key=len, reverse=True))
_PATCHER_PATTERN = "|".join(sorted(_KNOWN_PATCHERS, key=len, reverse=True))

# Primary pattern: matches <app>[-<patcher>]-v<version>-<arch>.apk
# e.g. twitter-piko-v12.29.1-prod.01-all.apk
#      googlephotos-devanced-v7.92.0.977185651-all.apk
#      music-morphe-v9.20.53-arm64-v8a.apk
_FILENAME_RE = re.compile(
    rf"^(?P<app>.+?)(?:-(?P<patcher>{_PATCHER_PATTERN}))?-v(?P<version>.+)-(?P<arch>{_ARCH_PATTERN})\.apk$",
    re.IGNORECASE,
)


def _format_app_name(raw: str) -> str:
    """Format app identifier to its canonical display name."""
    key = raw.lower().strip()
    if key in _APP_DISPLAY_NAMES:
        return _APP_DISPLAY_NAMES[key]
    return raw.replace("-", " ").title()


def _split_version_arch(version_arch: str) -> tuple[str, str]:
    """Handle filenames where version and arch share hyphen-delimited segments.

    e.g. ``9.15.51-arm64-v8a`` → ``('9.15.51', 'arm64-v8a')``
         ``12.29.1-prod.01-all`` → ``('12.29.1-prod.01', 'all')``
    """
    for arch in sorted(_KNOWN_ARCHS, key=len, reverse=True):
        if version_arch.lower().endswith(f"-{arch}"):
            ver = version_arch[: -(len(arch) + 1)]
            if ver:
                return ver, arch
    if "-" in version_arch:
        ver, arch = version_arch.rsplit("-", 1)
        if ver and arch:
            return ver, arch
    return version_arch, "unknown"


def _parse_apk_name(filename: str) -> AppInfo:
    """Extract app name, version, and architecture from the APK filename."""
    if m := _FILENAME_RE.match(filename):
        app_name = _format_app_name(m.group("app"))
        version = m.group("version").removeprefix("v")
        arch = m.group("arch")
        return app_name, version, arch

    # Fallback for unexpected naming schemes
    stem = Path(filename).stem
    if "-v" in stem:
        prefix, version_arch = stem.split("-v", 1)
        for patcher in sorted(_KNOWN_PATCHERS, key=len, reverse=True):
            if prefix.lower().endswith(f"-{patcher}"):
                prefix = prefix[: -(len(patcher) + 1)]
                break
        ver, arch = _split_version_arch(version_arch)
        return _format_app_name(prefix), ver.removeprefix("v"), arch

    return stem, "unknown", "unknown"


def _build_caption(asset: ReleaseAsset, release_tag: str) -> str:
    name, version, arch = _parse_apk_name(asset.name)
    emoji = _APP_EMOJI.get(name.lower(), _APP_EMOJI.get(name.split()[0].lower(), "📦"))
    size_mb = asset.size / (1024 * 1024)
    ver_str = f"v{version}" if version != "unknown" else "unknown"
    return (
        f"{emoji} **{name} ReVanced**\n"
        f"📌 Version: `{ver_str}`\n"
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
