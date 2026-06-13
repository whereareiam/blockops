from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests


class HangarClient:
    def __init__(self, token: str, api_base: str = "https://hangar.papermc.io/api/v1") -> None:
        self.api_base = api_base.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "blockops-publish/0.2.0"})
        self._bearer_token: str | None = None

    def authenticate(self) -> None:
        if self._bearer_token:
            return
        response = self.session.post(
            f"{self.api_base}/authenticate",
            params={"apiKey": self.token},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("token") if isinstance(data, dict) else None
        if not isinstance(token, str) or not token:
            raise RuntimeError("Hangar authentication response did not contain a token")
        self._bearer_token = token
        self.session.headers["Authorization"] = f"Bearer {token}"

    def upload_version(self, project_slug: str, payload: dict[str, Any], artifact_path: Path) -> dict[str, Any]:
        self.authenticate()
        with artifact_path.open("rb") as artifact_handle:
            response = self.session.post(
                f"{self.api_base}/projects/{project_slug}/upload",
                files=[
                    ("versionUpload", (None, json.dumps(payload), "application/json")),
                    ("files", (artifact_path.name, artifact_handle, "application/java-archive")),
                ],
                timeout=120,
            )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {}
