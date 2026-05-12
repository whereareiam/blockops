from __future__ import annotations

from typing import Protocol


class VersionSource(Protocol):
    def resolve_latest(self, source: dict, version_kind: str) -> list[str]: ...
