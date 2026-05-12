from __future__ import annotations

from pathlib import Path

from blockops_publish.providers.base import PublishContext
from blockops_publish.providers.hangar.client import HangarClient


class HangarPublishError(RuntimeError):
    """Raised when Hangar publishing cannot continue safely."""


class HangarPublisher:
    def __init__(self, token: str) -> None:
        self.token = token
        self.client = HangarClient(token)

    def publish(self, release, target, artifact_path: Path, dry_run: bool) -> str:
        project_slug = target.provider.get("project_slug")
        if not isinstance(project_slug, str) or not project_slug:
            raise HangarPublishError(f"Hangar publication {target.publication} must define project_slug")

        payload = self._build_payload(release, target)
        if dry_run:
            return f"Dry run validated Hangar publication {target.publication}"
        if not self.token:
            raise HangarPublishError("Hangar token is required for non-dry-run publishing")

        context = PublishContext(release=release, target=target, artifact_path=artifact_path)
        self.client.upload_version(project_slug, payload, artifact_path)
        return f"Published Hangar publication {target.publication}"

    def _build_payload(self, release, target) -> dict:
        dependencies = [dict(dependency) for dependency in target.provider.get("dependencies", [])]
        platform_dependencies = {}
        plugin_dependencies = {}
        for platform in target.selected_platforms:
            artifact_platform = target.artifact.platforms[platform]
            platform_dependencies[platform] = artifact_platform.platform_versions
            plugin_dependencies[platform] = dependencies

        return {
            "version": release.version_number,
            "channel": self._provider_release_channel(target, release.version_type),
            "description": release.changelog,
            "platformDependencies": platform_dependencies,
            "pluginDependencies": plugin_dependencies,
            "files": [
                {
                    "platforms": target.selected_platforms,
                    "externalUrl": release.html_url,
                }
            ],
        }

    def _provider_release_channel(self, target, version_type: str) -> str:
        mapping = target.provider.get("release_type_map", {})
        mapped = mapping.get(version_type)
        if isinstance(mapped, str) and mapped:
            return mapped
        return "Release" if version_type == "release" else "Beta"
