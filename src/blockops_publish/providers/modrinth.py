from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

from blockops_publish.publish.models import PublishTarget, ReleaseMetadata


class ModrinthPublishError(RuntimeError):
    """Raised when Modrinth publishing cannot continue safely."""


class ModrinthPublisher:
    def __init__(self, token: str, api_base: str = "https://api.modrinth.com/v3") -> None:
        self.api_base = api_base.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "blockops-publish/0.1.0"})
        if token:
            self.session.headers["Authorization"] = token

    def publish(self, release: ReleaseMetadata, target: PublishTarget, artifact_path: Path, dry_run: bool) -> str:
        project_id = self._get_project_id(target)
        payload = self._build_payload(release, target)
        existing_versions = self._get_project_versions(project_id)
        status = self._classify_existing(payload, target, existing_versions)
        if status == "skip":
            return f"Skipped existing Modrinth publication {target.publication}"
        if status == "conflict":
            raise ModrinthPublishError(
                f"Conflicting Modrinth version already exists for {target.publication} "
                f"({target.artifact.artifact_name}, {release.version_number})"
            )
        if dry_run:
            return f"Dry run validated Modrinth publication {target.publication}"

        if not self.token:
            raise ModrinthPublishError("Modrinth token is required for non-dry-run publishing")

        self._create_version(payload, artifact_path)
        return f"Published Modrinth publication {target.publication}"

    def _get_project_versions(self, project_id: str) -> list[dict[str, Any]]:
        response = self.session.get(f"{self.api_base}/project/{project_id}/version", timeout=30)
        if response.status_code >= 400:
            raise ModrinthPublishError(
                f"Failed to query existing Modrinth versions for {project_id}: "
                f"{response.status_code} {response.text}"
            )
        data = response.json()
        return data if isinstance(data, list) else []

    def _classify_existing(
        self,
        payload: dict[str, Any],
        target: PublishTarget,
        existing_versions: list[dict[str, Any]],
    ) -> str:
        expected_file = target.artifact.artifact_name
        expected_loaders = sorted(payload["loaders"])
        expected_games = sorted(payload["game_versions"])

        for version in existing_versions:
            files = version.get("files") or []
            filenames = sorted(file["filename"] for file in files if "filename" in file)
            same_file = expected_file in filenames
            same_loaders = sorted(version.get("loaders") or []) == expected_loaders

            if not (same_file or same_loaders):
                continue

            exact_match = (
                version.get("version_number") == payload["version_number"]
                and version.get("name") == payload["name"]
                and (version.get("changelog") or "") == payload["changelog"]
                and version.get("version_type") == payload["version_type"]
                and sorted(version.get("loaders") or []) == expected_loaders
                and sorted(version.get("game_versions") or []) == expected_games
                and same_file
            )
            if exact_match:
                return "skip"

            return "conflict"

        return "publish"

    def _get_project_id(self, target: PublishTarget) -> str:
        project_id = target.provider_config.get("project_id")
        if not isinstance(project_id, str) or not project_id:
            raise ModrinthPublishError(
                f"Modrinth publication {target.publication} must define project_id"
            )
        return project_id

    def _build_payload(self, release: ReleaseMetadata, target: PublishTarget) -> dict[str, Any]:
        project_id = self._get_project_id(target)
        if not target.artifact.loaders:
            raise ModrinthPublishError(
                f"Artifact {target.artifact.name} must define loaders for Modrinth publishing"
            )

        return {
            "name": release.title,
            "version_number": release.version_number,
            "changelog": release.changelog,
            "dependencies": self._build_dependencies(target),
            "game_versions": target.artifact.game_versions,
            "version_type": release.version_type,
            "loaders": target.artifact.loaders,
            "featured": False,
            "status": "listed",
            "project_id": project_id,
            "file_parts": [target.artifact.artifact_name],
            "primary_file": target.artifact.artifact_name,
        }

    def _create_version(self, payload: dict[str, Any], artifact_path: Path) -> None:
        with artifact_path.open("rb") as artifact_handle:
            response = self.session.post(
                f"{self.api_base}/version",
                data={"data": json.dumps(payload)},
                files={artifact_path.name: (artifact_path.name, artifact_handle, "application/java-archive")},
                timeout=120,
            )

        if response.status_code >= 400:
            raise ModrinthPublishError(
                f"Failed to create Modrinth version {payload['version_number']} for {artifact_path.name}: "
                f"{response.status_code} {response.text}"
            )

    def _build_dependencies(self, target: PublishTarget) -> list[dict[str, Any]]:
        raw_dependencies = target.provider_config.get("dependencies", [])
        if not isinstance(raw_dependencies, list):
            raise ModrinthPublishError(
                f"Modrinth publication {target.publication} dependencies must be a list when defined"
            )

        dependencies: list[dict[str, Any]] = []
        for dependency in raw_dependencies:
            if not isinstance(dependency, dict):
                raise ModrinthPublishError(
                    f"Modrinth publication {target.publication} dependencies must be mappings"
                )

            dependency_type = dependency.get("dependency_type")
            if dependency_type not in {"required", "optional", "incompatible", "embedded"}:
                raise ModrinthPublishError(
                    f"Modrinth publication {target.publication} dependency_type must be one of "
                    f"required, optional, incompatible, embedded"
                )

            project_id = dependency.get("project_id")
            version_id = dependency.get("version_id")
            file_name = dependency.get("file_name")
            if not any(isinstance(value, str) and value for value in (project_id, version_id, file_name)):
                raise ModrinthPublishError(
                    f"Modrinth publication {target.publication} dependencies must define project_id, version_id, "
                    f"or file_name"
                )

            payload = {"dependency_type": dependency_type}
            if isinstance(project_id, str) and project_id:
                payload["project_id"] = project_id
            if isinstance(version_id, str) and version_id:
                payload["version_id"] = version_id
            if isinstance(file_name, str) and file_name:
                payload["file_name"] = file_name
            dependencies.append(payload)

        return dependencies
