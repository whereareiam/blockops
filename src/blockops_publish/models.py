from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
class PublishTarget:
    provider: str
    variant: str
    artifact_name: str
    artifact_path: Path
    game_versions: list[str]
    loader_values: list[str]
    project_id: str


@dataclass(frozen=True)
class PublishPlan:
    release: ReleaseMetadata
    targets: list[PublishTarget]
