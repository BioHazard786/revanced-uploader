"""Pipeline orchestrator — asyncio.Queue-based poller / worker architecture."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import structlog

from revanced_bot.config import Settings
from revanced_bot.github import GitHubClient
from revanced_bot.models import ReleaseAsset
from revanced_bot.state import StateManager
from revanced_bot.telegram import TelegramService

log = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class UploadTask:
    """A unit of work: one APK to download and upload."""

    asset: ReleaseAsset
    release_tag: str


class PipelineOrchestrator:
    """Coordinates a single poller and *N* workers via an asyncio.Queue.

    Poller  ──▶  asyncio.Queue[UploadTask | None]  ──▶  Worker(s)
    """

    def __init__(
        self,
        *,
        github: GitHubClient,
        telegram: TelegramService,
        state: StateManager,
        settings: Settings,
    ) -> None:
        self._github = github
        self._telegram = telegram
        self._state = state
        self._settings = settings
        self._queue: asyncio.Queue[UploadTask | None] = asyncio.Queue()
        self._shutdown_event = asyncio.Event()

    # ── poller ────────────────────────────────────────────────

    async def _poller(self) -> None:
        """Periodically fetch the latest release and enqueue new APKs."""
        log.info(
            "poller_started",
            repo=self._settings.github_repo,
            interval_s=self._settings.poll_interval,
        )

        while not self._shutdown_event.is_set():
            try:
                release = await self._github.get_latest_release()
                last_tag = await self._state.get_last_tag()

                if release.tag_name != last_tag:
                    apks = self._github.filter_apk_assets(release)
                    log.info(
                        "new_release_found",
                        tag=release.tag_name,
                        apk_count=len(apks),
                        names=[a.name for a in apks],
                    )

                    for asset in apks:
                        await self._queue.put(
                            UploadTask(asset=asset, release_tag=release.tag_name),
                        )

                    # Block until every queued item has been processed
                    await self._queue.join()

                    # All uploads succeeded — persist the tag
                    await self._state.set_last_tag(release.tag_name)
                    log.info("release_fully_uploaded", tag=release.tag_name)
                else:
                    log.debug("no_new_release", current_tag=last_tag)

            except Exception:
                log.exception("poller_error")

            # Sleep until next poll — or wake early on shutdown
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self._settings.poll_interval,
                )
            except TimeoutError:
                pass

        log.info("poller_stopped")

    # ── worker ────────────────────────────────────────────────

    async def _worker(self, worker_id: int) -> None:
        """Pull tasks from the queue, download, and upload."""
        log.info("worker_started", worker_id=worker_id)

        while True:
            task = await self._queue.get()

            # None is the shutdown sentinel
            if task is None:
                self._queue.task_done()
                break

            file_path: Path | None = None
            try:
                file_path = await self._github.download_asset(task.asset)
                await self._telegram.upload_apk(
                    file_path, task.asset, task.release_tag,
                )
            except Exception:
                log.exception(
                    "worker_task_failed",
                    asset=task.asset.name,
                    worker_id=worker_id,
                )
            finally:
                # Clean up temp file regardless of outcome
                if file_path and file_path.exists():
                    file_path.unlink()
                    log.debug("temp_cleaned", path=str(file_path))
                self._queue.task_done()

        log.info("worker_stopped", worker_id=worker_id)

    # ── lifecycle ─────────────────────────────────────────────

    async def run(self) -> None:
        """Start poller + workers inside a TaskGroup."""
        n = self._settings.num_workers
        async with asyncio.TaskGroup() as tg:
            self._tasks = [
                tg.create_task(self._poller(), name="poller")
            ]
            for i in range(n):
                self._tasks.append(
                    tg.create_task(self._worker(i), name=f"worker-{i}")
                )

    async def shutdown(self) -> None:
        """Signal all coroutines to exit gracefully."""
        self._shutdown_event.set()
        # Cancel all running tasks so they stop immediately
        if hasattr(self, "_tasks"):
            for t in self._tasks:
                t.cancel()
        
        # Unblock every worker with a None sentinel (fallback)
        for _ in range(self._settings.num_workers):
            await self._queue.put(None)
