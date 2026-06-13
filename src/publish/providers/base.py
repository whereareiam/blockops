from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel

from publish.models import ArtifactPlatformSpec, ReleaseMetadata, ResolvedPublishTarget
from publish.version_sources.resolver import VersionSourceResolver


@dataclass
class PublishContext:
    release: ReleaseMetadata
    target: ResolvedPublishTarget
    artifact_path: Path
    provider_state: dict[str, Any] = field(default_factory=dict)


class Publisher(Protocol):
    def publish(
        self,
        release: ReleaseMetadata,
        target: ResolvedPublishTarget,
        artifact_path: Path,
        dry_run: bool,
    ) -> str: ...


class ProviderDefinition(Protocol):
    id: str
    config_model: type[BaseModel]

    def parse_provider(self, publication: str, provider_data: dict[str, Any]) -> dict[str, Any]: ...

    def resolve_target(
        self,
        release: ReleaseMetadata,
        target: ResolvedPublishTarget,
        unresolved_platforms: dict[str, ArtifactPlatformSpec],
        resolver: VersionSourceResolver,
    ) -> None: ...

    def build_publisher(self, credentials: str) -> Publisher: ...
