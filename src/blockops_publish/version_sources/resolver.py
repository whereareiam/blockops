from __future__ import annotations

from typing import Any

from blockops_publish.manifest.config import ConfigError
from blockops_publish.version_sources.source import VersionSource
from blockops_publish.version_sources.type.fill import PaperMcFillProjectVersionSource


class VersionSourceResolver:
    def __init__(self, sources: dict[str, VersionSource] | None = None) -> None:
        self.sources = sources or {
            PaperMcFillProjectVersionSource.SOURCE_TYPE: PaperMcFillProjectVersionSource(),
        }
        self.default_sources: dict[str, dict[str, str]] = {
            "game_versions": {
                "type": PaperMcFillProjectVersionSource.SOURCE_TYPE,
                "project": "paper",
            },
            "platform_versions": {
                "type": PaperMcFillProjectVersionSource.SOURCE_TYPE,
                "project": "velocity",
            },
        }

    def resolve_latest(self, source: dict[str, Any], version_kind: str) -> list[str]:
        source_type = source.get("type")
        if not isinstance(source_type, str) or not source_type:
            raise ConfigError(f"{version_kind} source must define type")

        implementation = self.sources.get(source_type)
        if implementation is None:
            raise ConfigError(f"Unsupported {version_kind} source type: {source_type}")

        return implementation.resolve_latest(source, version_kind)

    def resolve_latest_default(self, version_kind: str) -> list[str]:
        source = self.default_sources.get(version_kind)
        if source is None:
            raise ConfigError(f"No default version source configured for {version_kind}")
        return self.resolve_latest(source, version_kind)
