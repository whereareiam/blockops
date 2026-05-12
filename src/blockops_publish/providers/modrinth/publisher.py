from __future__ import annotations

from pathlib import Path

from blockops_publish.providers.base import PublishContext
from blockops_publish.providers.modrinth.client import ModrinthClient
from blockops_publish.providers.modrinth.existing_version import ModrinthExistingVersionChecker


class ModrinthPublishError(RuntimeError):
    """Raised when Modrinth publishing cannot continue safely."""


class ModrinthPublisher:
    def __init__(self, token: str) -> None:
        self.token = token
        self.client = ModrinthClient(token)
        self.existing_version_checker = ModrinthExistingVersionChecker()

    def publish(self, release, target, artifact_path: Path, dry_run: bool) -> str:
        project_id = target.provider.get("project_id")
        if not isinstance(project_id, str) or not project_id:
            raise ModrinthPublishError(f"Modrinth publication {target.publication} must define project_id")

        payload = self._build_payload(release, target)
        existing_versions = self.client.list_project_versions(project_id)
        status = self.existing_version_checker.classify(release, target, existing_versions)
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

        upload_result = self.client.create_version(payload, artifact_path)
        context = PublishContext(release=release, target=target, artifact_path=artifact_path)
        self._apply_reclassify(context, upload_result)
        return f"Published Modrinth publication {target.publication}"

    def _build_payload(self, release, target) -> dict:
        game_versions = sorted(self._game_versions(target))
        loaders = sorted(self._upload_loaders(target))
        if not loaders:
            raise ModrinthPublishError(f"Publication {target.publication} must resolve at least one loader")

        return {
            "name": release.title,
            "version_number": release.version_number,
            "changelog": release.changelog,
            "dependencies": self._build_dependencies(target),
            "game_versions": game_versions,
            "version_type": self._provider_version_type(target, release.version_type),
            "loaders": loaders,
            "featured": False,
            "status": "listed",
            "project_id": target.provider["project_id"],
            "file_parts": [target.artifact.artifact_name],
            "primary_file": target.artifact.artifact_name,
        }

    def _loaders(self, target) -> list[str]:
        loaders: list[str] = []
        for platform in target.selected_platforms:
            loaders.extend(target.artifact.platforms[platform].loaders)
        return loaders

    def _game_versions(self, target) -> list[str]:
        versions: list[str] = []
        for platform in target.selected_platforms:
            versions.extend(target.artifact.platforms[platform].game_versions)
        return versions

    def _upload_loaders(self, target) -> list[str]:
        loaders = target.provider.get("upload_loaders")
        if isinstance(loaders, list) and all(isinstance(item, str) and item for item in loaders):
            return loaders
        return self._loaders(target)

    def _build_dependencies(self, target) -> list[dict]:
        dependencies = target.provider.get("dependencies", [])
        return [dict(dependency) for dependency in dependencies]

    def _apply_reclassify(self, context: PublishContext, upload_result: dict) -> None:
        version_id = upload_result.get("id")
        if not isinstance(version_id, str) or not version_id:
            raise RuntimeError("Modrinth reclassify requires returned version id")

        config = context.target.provider.get("reclassify")
        if not isinstance(config, dict):
            return

        payload = {}
        loaders = config.get("loaders")
        if isinstance(loaders, list) and loaders:
            payload["loaders"] = sorted(loaders)
        else:
            payload["loaders"] = sorted(self._loaders(context.target))

        version_type = config.get("version_type")
        if isinstance(version_type, str) and version_type:
            payload["version_type"] = version_type

        status = config.get("status")
        if isinstance(status, str) and status:
            payload["status"] = status

        self.client.modify_version(version_id, payload)

    def _provider_version_type(self, target, version_type: str) -> str:
        mapping = target.provider.get("release_type_map", {})
        mapped = mapping.get(version_type)
        if isinstance(mapped, str) and mapped:
            return mapped
        return version_type
