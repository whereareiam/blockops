from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests


class ModrinthClient:
    def __init__(self, token: str, api_base: str = "https://api.modrinth.com/v3") -> None:
        self.api_base = api_base.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "blockops-publish/0.1.0"})
        if token:
            self.session.headers["Authorization"] = token

    def list_project_versions(self, project_id: str) -> list[dict[str, Any]]:
        response = self.session.get(f"{self.api_base}/project/{project_id}/version", timeout=30)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []

    def create_version(self, payload: dict[str, Any], artifact_path: Path) -> dict[str, Any]:
        with artifact_path.open("rb") as artifact_handle:
            response = self.session.post(
                f"{self.api_base}/version",
                data={"data": json.dumps(payload)},
                files={artifact_path.name: (artifact_path.name, artifact_handle, "application/java-archive")},
                timeout=120,
            )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {}

    def modify_version(self, version_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.session.patch(
            f"{self.api_base}/version/{version_id}",
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {}
