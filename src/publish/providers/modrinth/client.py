from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests


class ModrinthApiError(RuntimeError):
    """Raised when the Modrinth API rejects a request."""


class ModrinthClient:
    def __init__(self, token: str, api_base: str = "https://api.modrinth.com/v3") -> None:
        self.api_base = api_base.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "blockops-publish/0.2.0"})
        if token:
            self.session.headers["Authorization"] = token

    def list_project_versions(self, project_id: str) -> list[dict[str, Any]]:
        response = self.session.get(f"{self.api_base}/project/{project_id}/version", timeout=30)
        self._raise_for_status(response, "list project versions")
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
        self._raise_for_status(response, "create version")
        data = response.json()
        return data if isinstance(data, dict) else {}

    def modify_version(self, version_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.session.patch(
            f"{self.api_base}/version/{version_id}",
            json=payload,
            timeout=60,
        )
        self._raise_for_status(response, "modify version")
        data = response.json()
        return data if isinstance(data, dict) else {}

    def _raise_for_status(self, response: requests.Response, action: str) -> None:
        if response.status_code < 400:
            return

        detail = self._error_detail(response)
        raise ModrinthApiError(f"Modrinth {action} failed: {response.status_code} {detail}")

    def _error_detail(self, response: requests.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            return response.text.strip() or response.reason

        if isinstance(data, dict):
            error = data.get("error")
            description = data.get("description")
            if isinstance(error, str) and isinstance(description, str):
                return f"{error}: {description}"
            if isinstance(description, str):
                return description
            if isinstance(error, str):
                return error

        return response.text.strip() or response.reason
