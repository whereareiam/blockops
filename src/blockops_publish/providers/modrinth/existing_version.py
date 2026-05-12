from __future__ import annotations

from typing import Any

from blockops_publish.publish.models import ReleaseMetadata, ResolvedPublishTarget


class ModrinthExistingVersionChecker:
    def classify(self, release: ReleaseMetadata, target: ResolvedPublishTarget, existing_versions: list[dict[str, Any]]) -> str:
        expected_file = target.artifact.artifact_name
        expected_loaders = sorted(self._loaders(target))
        expected_games = sorted(self._game_versions(target))

        for version in existing_versions:
            files = version.get("files") or []
            filenames = sorted(file["filename"] for file in files if "filename" in file)
            same_file = expected_file in filenames
            same_number = version.get("version_number") == release.version_number
            same_loaders = sorted(version.get("loaders") or []) == expected_loaders

            if not (same_file or same_number):
                continue

            exact_match = (
                same_number
                and version.get("name") == release.title
                and (version.get("changelog") or "") == release.changelog
                and version.get("version_type") == release.version_type
                and same_loaders
                and sorted(version.get("game_versions") or []) == expected_games
                and same_file
            )
            if exact_match:
                return "skip"

            return "conflict"

        return "publish"

    def _loaders(self, target: ResolvedPublishTarget) -> list[str]:
        loaders: list[str] = []
        for platform in target.selected_platforms:
            loaders.extend(target.artifact.platforms[platform].loaders)
        return loaders

    def _game_versions(self, target: ResolvedPublishTarget) -> list[str]:
        values: list[str] = []
        for platform in target.selected_platforms:
            values.extend(target.artifact.platforms[platform].game_versions)
        return values
