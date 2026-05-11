from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from blockops_publish.publish.models import PublishTarget
from blockops_publish.providers.hangar import HangarPublisher
from blockops_publish.providers.modrinth import ModrinthPublisher
from blockops_publish.shared.config import ConfigError


def publish_single_target(
    release,
    target: PublishTarget,
    artifact_path: Path,
    dry_run: bool,
    modrinth_token: str,
    hangar_token: str,
    provider_clients: dict[str, Any] | None = None,
) -> str:
    provider_clients = provider_clients or {}

    if target.provider == "modrinth":
        provider_clients.setdefault("modrinth", ModrinthPublisher(modrinth_token))
        return provider_clients["modrinth"].publish(release, target, artifact_path=artifact_path, dry_run=dry_run)

    if target.provider == "hangar":
        provider_clients.setdefault("hangar", HangarPublisher(hangar_token))
        return provider_clients["hangar"].publish(release, target, artifact_path=artifact_path, dry_run=dry_run)

    raise ConfigError(f"Unsupported provider: {target.provider}")


def resolve_artifact_path(artifact_directory: Path, target) -> Path:
    artifact_path = artifact_directory / target.artifact.artifact_name
    if not artifact_path.is_file():
        raise ConfigError(f"Artifact file not found for publication {target.publication}: {artifact_path}")
    return artifact_path


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def write_step_summary(markdown: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with Path(summary_path).open("a", encoding="utf-8") as handle:
        handle.write(markdown)
        handle.write("\n")
