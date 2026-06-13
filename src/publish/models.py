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
class ArtifactPlatformSpec:
    key: str
    loaders: list[str]
    game_versions: list[str]
    platform_versions: list[str]
    game_versions_source: dict[str, Any] | None
    platform_versions_source: dict[str, Any] | None


@dataclass(frozen=True)
class ArtifactSpec:
    name: str
    file_template: str
    platforms: dict[str, ArtifactPlatformSpec]


@dataclass(frozen=True)
class PublicationSpec:
    provider_id: str
    publication: str
    artifact_name: str
    platforms: list[str] | None
    provider: dict[str, Any]


@dataclass(frozen=True)
class DistributionManifest:
    artifacts: dict[str, ArtifactSpec]
    publications: dict[str, PublicationSpec]


@dataclass
class ResolvedArtifactPlatform:
    key: str
    loaders: list[str]
    game_versions: list[str]
    platform_versions: list[str]


@dataclass
class ResolvedArtifact:
    name: str
    file_template: str
    artifact_name: str
    platforms: dict[str, ResolvedArtifactPlatform]


@dataclass
class ResolvedPublishTarget:
    provider_id: str
    publication: str
    artifact: ResolvedArtifact
    selected_platforms: list[str]
    provider: dict[str, Any]


@dataclass
class ResolvedPublishPlan:
    release: ReleaseMetadata
    targets: list[ResolvedPublishTarget]
