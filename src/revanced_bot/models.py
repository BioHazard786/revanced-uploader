"""Domain models for GitHub releases and assets."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    """A single downloadable asset from a GitHub release."""

    name: str
    size: int
    download_url: str


@dataclass(frozen=True, slots=True)
class Release:
    """A GitHub release with its tag, metadata, and asset list."""

    tag_name: str
    published_at: str
    html_url: str
    assets: list[ReleaseAsset] = field(default_factory=list)
