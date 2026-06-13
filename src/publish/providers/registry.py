from __future__ import annotations

from publish.manifest.config import ConfigError
from publish.providers.base import ProviderDefinition
from publish.providers.hangar.provider import HangarProvider
from publish.providers.modrinth.provider import ModrinthProvider


class ProviderRegistry:
    def __init__(self, providers: list[ProviderDefinition] | None = None) -> None:
        resolved_providers = providers or [
            ModrinthProvider(),
            HangarProvider(),
        ]
        self.providers = {provider.id: provider for provider in resolved_providers}

    def get_provider(self, provider_id: str) -> ProviderDefinition:
        provider = self.providers.get(provider_id)
        if provider is None:
            raise ConfigError(f"Unsupported provider: {provider_id}")
        return provider
