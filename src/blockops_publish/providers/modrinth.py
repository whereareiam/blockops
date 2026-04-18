from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

from blockops_publish.models import PublishTarget, ReleaseMetadata


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

    def publish(self, release: ReleaseMetadata, target: PublishTarget, dry_run: bool) -> str:
        payload = self._build_payload(release, target)
        existing_versions = self._get_project_versions(target.project_id)
        status = self._classify_existing(payload, target, existing_versions)
        if status == "skip":
            return f"Skipped existing Modrinth target {target.provider}:{target.variant}"
        if status == "conflict":
            raise ModrinthPublishError(
                f"Conflicting Modrinth version already exists for {target.provider}:{target.variant} "
                f"({target.artifact_name}, {release.version_number})"
            )
        if dry_run:
            return f"Dry run validated Modrinth target {target.provider}:{target.variant}"

        if not self.token:
            raise ModrinthPublishError("Modrinth token is required for non-dry-run publishing")

        self._create_version(payload, target.artifact_path)
        return f"Published Modrinth target {target.provider}:{target.variant}"

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
        expected_file = target.artifact_name
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

    def _build_payload(self, release: ReleaseMetadata, target: PublishTarget) -> dict[str, Any]:
        return {
            "name": release.title,
            "version_number": release.version_number,
            "changelog": release.changelog,
            "dependencies": [],
            "game_versions": target.game_versions,
            "version_type": release.version_type,
            "loaders": target.loader_values,
            "featured": False,
            "status": "listed",
            "project_id": target.project_id,
            "file_parts": [target.artifact_name],
            "primary_file": target.artifact_name,
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
