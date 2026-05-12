from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from blockops_publish.providers.registry import ProviderRegistry


def publish_single_target(
    release,
    target,
    artifact_path: Path,
    dry_run: bool,
    provider_credentials: dict[str, str],
    provider_registry: ProviderRegistry | None = None,
) -> str:
    provider_registry = provider_registry or ProviderRegistry()
    provider = provider_registry.get_provider(target.provider_id)
    publisher = provider.build_publisher(provider_credentials.get(target.provider_id, ""))
    return publisher.publish(release, target, artifact_path=artifact_path, dry_run=dry_run)


def resolve_artifact_path(artifact_directory: Path, target) -> Path:
    artifact_path = artifact_directory / target.artifact.artifact_name
    if not artifact_path.is_file():
        raise ValueError(f"Artifact file not found for publication {target.publication}: {artifact_path}")
    return artifact_path


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_provider_credentials(raw: str) -> dict[str, str]:
    if not raw.strip():
        return {}

    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError("Provider credentials must be a mapping")

    credentials: dict[str, str] = {}
    for provider_id, credential in data.items():
        if not isinstance(provider_id, str) or not provider_id:
            raise ValueError("Provider credential keys must be non-empty strings")
        if not isinstance(credential, str):
            raise ValueError(f"Provider credential for {provider_id} must be a string")
        credentials[provider_id] = credential
    return credentials


def write_step_summary(markdown: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with Path(summary_path).open("a", encoding="utf-8") as handle:
        handle.write(markdown)
        handle.write("\n")
