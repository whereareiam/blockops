from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

from blockops_publish.publish.models import PublishTarget, ReleaseMetadata


class HangarPublishError(RuntimeError):
    """Raised when Hangar publishing cannot continue safely."""


class HangarPublisher:
    def __init__(self, token: str, api_base: str = "https://hangar.papermc.io/api/v1") -> None:
        self.api_base = api_base.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "blockops-publish/0.1.0"})
        self._bearer_token: str | None = None

    def publish(self, release: ReleaseMetadata, target: PublishTarget, artifact_path: Path, dry_run: bool) -> str:
        project_slug = self._get_project_slug(target)
        payload = self._build_payload(release, target, artifact_path)
        if dry_run:
            return f"Dry run validated Hangar publication {target.publication}"

        if not self.token:
            raise HangarPublishError("Hangar token is required for non-dry-run publishing")

        self._authenticate()
        self._upload(project_slug, payload, artifact_path)
        return f"Published Hangar publication {target.publication}"

    def _authenticate(self) -> None:
        if self._bearer_token:
            return

        response = self.session.post(
            f"{self.api_base}/authenticate",
            params={"apiKey": self.token},
            timeout=30,
        )
        if response.status_code >= 400:
            raise HangarPublishError(
                f"Failed to authenticate with Hangar: {response.status_code} {response.text}"
            )

        data = response.json()
        token = data.get("token")
        if not isinstance(token, str) or not token:
            raise HangarPublishError("Hangar authentication response did not contain a token")

        self._bearer_token = token
        self.session.headers["Authorization"] = f"Bearer {token}"

    def _upload(self, project_slug: str, payload: dict[str, Any], artifact_path: Path) -> None:
        with artifact_path.open("rb") as artifact_handle:
            response = self.session.post(
                f"{self.api_base}/projects/{project_slug}/upload",
                data={"versionUpload": json.dumps(payload)},
                files={
                    "files": (
                        artifact_path.name,
                        artifact_handle,
                        "application/java-archive",
                    )
                },
                timeout=120,
            )

        if response.status_code >= 400:
            raise HangarPublishError(
                f"Failed to upload Hangar version {payload['version']} for {artifact_path.name}: "
                f"{response.status_code} {response.text}"
            )

    def _get_project_slug(self, target: PublishTarget) -> str:
        project_slug = target.provider_config.get("project_slug")
        if not isinstance(project_slug, str) or not project_slug:
            raise HangarPublishError(
                f"Hangar publication {target.publication} must define project_slug"
            )
        return project_slug

    def _build_payload(
        self,
        release: ReleaseMetadata,
        target: PublishTarget,
        artifact_path: Path,
    ) -> dict[str, Any]:
        channel = target.provider_config.get("channel")
        if channel is None:
            channel = self._resolve_channel(release)
        if not isinstance(channel, str) or not channel:
            raise HangarPublishError(f"Hangar publication {target.publication} must define a valid channel")

        platform = target.provider_config.get("platform", target.artifact.platform)
        if not isinstance(platform, str) or not platform:
            raise HangarPublishError(
                f"Hangar publication {target.publication} must define platform or artifact platform"
            )

        raw_versions = target.provider_config.get("platform_versions", target.artifact.game_versions)
        if not isinstance(raw_versions, list) or not raw_versions or not all(isinstance(item, str) and item for item in raw_versions):
            raise HangarPublishError(
                f"Hangar publication {target.publication} must define platform_versions as a non-empty list of strings"
            )

        return {
            "version": release.version_number,
            "channel": channel,
            "description": release.changelog,
            "platformDependencies": {
                platform: raw_versions,
            },
            "pluginDependencies": {
                platform: self._build_dependencies(target),
            },
            "files": [
                {
                    "platforms": [platform],
                    "externalUrl": release.html_url,
                }
            ],
        }

    def _resolve_channel(self, release: ReleaseMetadata) -> str:
        if release.version_type == "release":
            return "Release"
        return "Beta"

    def _build_dependencies(self, target: PublishTarget) -> list[dict[str, Any]]:
        raw_dependencies = target.provider_config.get("dependencies", [])
        if not isinstance(raw_dependencies, list):
            raise HangarPublishError(
                f"Hangar publication {target.publication} dependencies must be a list when defined"
            )

        dependencies: list[dict[str, Any]] = []
        for dependency in raw_dependencies:
            if not isinstance(dependency, dict):
                raise HangarPublishError(
                    f"Hangar publication {target.publication} dependencies must be mappings"
                )

            kind = dependency.get("kind")
            name = dependency.get("name")
            required = dependency.get("required", True)
            if kind not in {"hangar", "url"}:
                raise HangarPublishError(
                    f"Hangar publication {target.publication} dependency kind must be hangar or url"
                )
            if not isinstance(name, str) or not name:
                raise HangarPublishError(
                    f"Hangar publication {target.publication} dependencies must define name"
                )
            if not isinstance(required, bool):
                raise HangarPublishError(
                    f"Hangar publication {target.publication} dependency required must be a boolean"
                )

            payload = {
                "name": name,
                "required": required,
            }
            if kind == "url":
                url = dependency.get("url")
                if not isinstance(url, str) or not url:
                    raise HangarPublishError(
                        f"Hangar publication {target.publication} url dependencies must define url"
                    )
                payload["externalUrl"] = url

            dependencies.append(payload)

        return dependencies
