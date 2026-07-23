"""Entry point — wires up services, runs the pipeline under uvloop."""

from __future__ import annotations

import asyncio
import logging
import signal

import structlog
import uvloop

from revanced_bot.config import Settings
from revanced_bot.github import GitHubClient
from revanced_bot.pipeline import PipelineOrchestrator
from revanced_bot.state import StateManager
from revanced_bot.telegram import TelegramService

log = structlog.get_logger()


# ── logging ───────────────────────────────────────────────────


def _configure_logging() -> None:
    """Set up structlog with stdlib integration so pyrogram logs are unified."""
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(),
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Quiet noisy pyrogram internals
    logging.getLogger("pyrogram").setLevel(logging.WARNING)


# ── shutdown watcher ──────────────────────────────────────────


async def _shutdown_watcher(
    event: asyncio.Event,
    pipeline: PipelineOrchestrator,
    telegram: TelegramService,
) -> None:
    """Wait for shutdown signal, then gracefully stop everything."""
    await event.wait()
    log.info("shutdown_signal_received")
    await pipeline.shutdown()
    await telegram.stop()


# ── main ──────────────────────────────────────────────────────


async def main() -> None:
    _configure_logging()

    settings = Settings()
    log.info(
        "config_loaded",
        channel=settings.channel_id,
        repo=settings.github_repo,
        poll_interval=settings.poll_interval,
        num_workers=settings.num_workers,
    )

    # Wire up OS signals → asyncio.Event
    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_event.set)

    # Initialise services
    github = GitHubClient(settings)
    state = StateManager(settings.state_file)
    telegram = TelegramService(settings)

    await telegram.start()

    pipeline = PipelineOrchestrator(
        github=github,
        telegram=telegram,
        state=state,
        settings=settings,
    )

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(
                _shutdown_watcher(shutdown_event, pipeline, telegram),
                name="shutdown-watcher",
            )
            tg.create_task(pipeline.run(), name="pipeline")
    finally:
        await github.close()
        log.info("shutdown_complete")


if __name__ == "__main__":
    uvloop.run(main())
