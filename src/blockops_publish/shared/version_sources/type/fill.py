from __future__ import annotations

from typing import Any

import requests

from blockops_publish.shared.config import ConfigError


class PaperMcFillProjectVersionSource:
    SOURCE_TYPE = "papermc-fill-project"

    def __init__(self, api_base: str = "https://fill.papermc.io/v3") -> None:
        self.api_base = api_base.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "blockops-publish/0.1.0"})
        self._cache: dict[str, dict[str, Any]] = {}

    def resolve_latest(self, source: dict[str, Any], version_kind: str) -> list[str]:
        project = source.get("project")
        if not isinstance(project, str) or not project:
            raise ConfigError(f"{version_kind} source must define project")

        data = self._get_fill_project(project)
        versions = data.get("versions")
        if not isinstance(versions, dict) or not versions:
            raise ConfigError(f"No versions returned for {project} from PaperMC Fill API")

        for candidates in versions.values():
            if not isinstance(candidates, list) or not candidates:
                continue
            for candidate in candidates:
                if isinstance(candidate, str) and candidate:
                    return [candidate]

        raise ConfigError(f"No usable versions returned for {project} from PaperMC Fill API")

    def _get_fill_project(self, project: str) -> dict[str, Any]:
        cached = self._cache.get(project)
        if cached is not None:
            return cached

        response = self.session.get(f"{self.api_base}/projects/{project}", timeout=30)
        if response.status_code >= 400:
            raise ConfigError(
                f"Failed to resolve versions for {project} from PaperMC Fill API: "
                f"{response.status_code} {response.text}"
            )

        data = response.json()
        if not isinstance(data, dict):
            raise ConfigError(f"Unexpected PaperMC Fill API response for {project}")

        self._cache[project] = data
        return data
