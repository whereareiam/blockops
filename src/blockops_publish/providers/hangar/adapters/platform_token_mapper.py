from __future__ import annotations


class HangarPlatformTokenMapper:
    def map(self, platform: str, raw_version: str) -> str:
        if platform != "velocity":
            return raw_version

        token = raw_version.split("-", 1)[0]
        parts = token.split(".")
        if len(parts) >= 2 and all(part.isdigit() for part in parts[:2]):
            return f"{parts[0]}.{parts[1]}"
        return raw_version
