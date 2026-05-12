from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when the distribution configuration is invalid."""


SUPPORTED_PROVIDERS = {"modrinth", "hangar"}


def load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"Manifest file does not exist: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ConfigError(f"Expected a mapping in manifest: {path}")

    return data


def load_override_file(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}

    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return {}

    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ConfigError("Override YAML must be a mapping at the top level")

    return data


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = deep_merge(current, value)
        else:
            merged[key] = deepcopy(value)
    return merged


def validate_manifest(manifest: dict[str, Any]) -> None:
    artifacts = manifest.get("artifacts")
    publications = manifest.get("publications")

    if not isinstance(artifacts, dict) or not artifacts:
        raise ConfigError("artifacts must be a non-empty mapping")

    if not isinstance(publications, dict) or not publications:
        raise ConfigError("publications must be a non-empty mapping")

    for artifact_name, artifact in artifacts.items():
        if not isinstance(artifact, dict):
            raise ConfigError(f"Artifact {artifact_name} must be a mapping")

        file_template = artifact.get("file")
        game_versions = artifact.get("game_versions")
        platform_versions = artifact.get("platform_versions", [])
        game_versions_source = artifact.get("game_versions_source")
        platform_versions_source = artifact.get("platform_versions_source")
        loaders = artifact.get("loaders", [])
        platform = artifact.get("platform")

        if not isinstance(file_template, str) or not file_template:
            raise ConfigError(f"Artifact {artifact_name} must define file")

        if game_versions is None:
            game_versions = []
        if not isinstance(game_versions, list) or not all(isinstance(item, str) for item in game_versions):
            raise ConfigError(f"Artifact {artifact_name} game_versions must be a list of strings")

        if not isinstance(loaders, list) or not all(isinstance(item, str) for item in loaders):
            raise ConfigError(f"Artifact {artifact_name} loaders must be a list of strings")

        if not isinstance(platform_versions, list) or not all(isinstance(item, str) for item in platform_versions):
            raise ConfigError(f"Artifact {artifact_name} platform_versions must be a list of strings")
        if game_versions_source is not None and not isinstance(game_versions_source, dict):
            raise ConfigError(f"Artifact {artifact_name} game_versions_source must be a mapping when defined")
        if platform_versions_source is not None and not isinstance(platform_versions_source, dict):
            raise ConfigError(f"Artifact {artifact_name} platform_versions_source must be a mapping when defined")

        if platform is not None and not isinstance(platform, str):
            raise ConfigError(f"Artifact {artifact_name} platform must be a string when defined")

    for publication_name, publication in publications.items():
        if not isinstance(publication, dict):
            raise ConfigError(f"Publication {publication_name} must be a mapping")

        provider = publication.get("provider")
        artifact_name = publication.get("artifact")

        if not isinstance(provider, str) or not provider:
            raise ConfigError(f"Publication {publication_name} must define provider")

        if provider not in SUPPORTED_PROVIDERS:
            raise ConfigError(
                f"Publication {publication_name} must define a supported provider: {sorted(SUPPORTED_PROVIDERS)}"
            )

        if not isinstance(artifact_name, str) or not artifact_name:
            raise ConfigError(f"Publication {publication_name} must define artifact")

        if artifact_name not in artifacts:
            raise ConfigError(
                f"Publication {publication_name} references unknown artifact {artifact_name}"
            )

        if provider == "hangar":
            project_slug = publication.get("project_slug")
            if not isinstance(project_slug, str) or not project_slug:
                raise ConfigError(f"Publication {publication_name} must define project_slug")

            channel = publication.get("channel")
            if channel is not None and (not isinstance(channel, str) or not channel):
                raise ConfigError(f"Publication {publication_name} channel must be a non-empty string when defined")

            platform = publication.get("platform", artifacts[artifact_name].get("platform"))
            if not isinstance(platform, str) or not platform:
                raise ConfigError(
                    f"Publication {publication_name} must define platform or artifact platform"
                )

            platform_versions = publication.get("platform_versions", artifacts[artifact_name].get("platform_versions"))
            if not platform_versions and (
                isinstance(artifacts[artifact_name].get("platform_versions_source"), dict)
                or artifacts[artifact_name].get("platform_versions_source") is None
            ):
                platform_versions = ["resolved-from-source"]
            if not isinstance(platform_versions, list) or not platform_versions:
                raise ConfigError(
                    f"Publication {publication_name} must define platform_versions as a non-empty list"
                )
            if not all(isinstance(item, str) and item for item in platform_versions):
                raise ConfigError(
                    f"Publication {publication_name} platform_versions must be a list of strings"
                )

        dependencies = publication.get("dependencies")
        if dependencies is not None and not isinstance(dependencies, list):
            raise ConfigError(f"Publication {publication_name} dependencies must be a list when defined")
