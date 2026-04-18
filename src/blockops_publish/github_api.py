from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import requests


class GitHubApiError(RuntimeError):
    """Raised when a GitHub API request fails."""


@dataclass(frozen=True)
class GitHubAsset:
    name: str
    api_url: str
    browser_download_url: str


@dataclass(frozen=True)
class GitHubRelease:
    tag_name: str
    name: str
    body: str
    html_url: str
    assets: list[GitHubAsset]


class GitHubClient:
    def __init__(self, repository: str, token: str) -> None:
        self.repository = repository
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "User-Agent": "blockops-publish/0.1.0",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def get_release_by_tag(self, tag: str) -> GitHubRelease:
        url = f"https://api.github.com/repos/{self.repository}/releases/tags/{tag}"
        response = self.session.get(url, timeout=30)
        if response.status_code >= 400:
            raise GitHubApiError(f"Failed to resolve release {tag}: {response.status_code} {response.text}")

        payload = response.json()
        return GitHubRelease(
            tag_name=payload["tag_name"],
            name=payload.get("name") or payload["tag_name"],
            body=payload.get("body") or "",
            html_url=payload["html_url"],
            assets=[
                GitHubAsset(
                    name=asset["name"],
                    api_url=asset["url"],
                    browser_download_url=asset["browser_download_url"],
                )
                for asset in payload.get("assets", [])
            ],
        )

    def download_asset(self, asset: GitHubAsset, destination: Path) -> Path:
        response = self.session.get(
            asset.api_url,
            headers={"Accept": "application/octet-stream"},
            stream=True,
            timeout=120,
        )
        if response.status_code >= 400:
            raise GitHubApiError(f"Failed to download asset {asset.name}: {response.status_code} {response.text}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    handle.write(chunk)

        return destination
