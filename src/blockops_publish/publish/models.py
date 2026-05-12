from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReleaseMetadata:
    repository: str
    tag_name: str
    version_number: str
    title: str
    changelog: str
    version_type: str
    html_url: str


@dataclass(frozen=True)
class PublishArtifact:
    name: str
    file_template: str
    artifact_name: str
    game_versions: list[str]
    platform_versions: list[str]
    game_versions_source: dict[str, Any] | None
    platform_versions_source: dict[str, Any] | None
    loaders: list[str]
    platform: str | None


@dataclass(frozen=True)
class PublishTarget:
    provider: str
    publication: str
    artifact: PublishArtifact
    provider_config: dict[str, Any]


@dataclass(frozen=True)
class PublishPlan:
    release: ReleaseMetadata
    targets: list[PublishTarget]
