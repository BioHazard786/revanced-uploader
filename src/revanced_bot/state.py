"""Persistent JSON state to track the last uploaded release tag."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger()


class StateManager:
    """Thread-safe, async JSON state backed by a single file."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()

    # ── private ───────────────────────────────────────────────

    async def _read(self) -> dict[str, Any]:
        def _do() -> dict[str, Any]:
            if not self._path.exists():
                return {}
            return json.loads(self._path.read_text(encoding="utf-8"))

        return await asyncio.to_thread(_do)

    async def _write(self, data: dict[str, Any]) -> None:
        def _do() -> None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        await asyncio.to_thread(_do)

    # ── public API ────────────────────────────────────────────

    async def get_last_tag(self) -> str | None:
        """Return the last successfully uploaded release tag, or *None*."""
        async with self._lock:
            data = await self._read()
            return data.get("last_tag")

    async def set_last_tag(self, tag: str) -> None:
        """Persist *tag* as the last successfully uploaded release."""
        async with self._lock:
            data = await self._read()
            data["last_tag"] = tag
            await self._write(data)
            log.info("state_updated", last_tag=tag)
