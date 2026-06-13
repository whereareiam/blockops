from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from publish.manifest.config import ConfigError
from publish.providers.base import ProviderDefinition
from publish.providers.hangar.adapters.platform_token_mapper import HangarPlatformTokenMapper
from publish.providers.hangar.publisher import HangarPublisher
from publish.models import ArtifactPlatformSpec, ReleaseMetadata, ResolvedPublishTarget
from publish.version_sources.resolver import VersionSourceResolver


class HangarDependencyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["hangar", "url"]
    name: str
    required: bool = True
    url: str | None = None


class HangarProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Literal["hangar"]
    project_slug: str
    dependencies: list[HangarDependencyModel] = Field(default_factory=list)
    release_type_map: dict[str, str] = Field(
        default_factory=lambda: {
            "release": "Release",
            "beta": "Beta",
            "alpha": "Beta",
        }
    )


class HangarProvider(ProviderDefinition):
    id = "hangar"
    config_model = HangarProviderConfig

    def __init__(self) -> None:
        self.mapper = HangarPlatformTokenMapper()

    def parse_provider(self, publication: str, provider_data: dict[str, Any]) -> dict[str, Any]:
        try:
            config = self.config_model.model_validate(provider_data)
        except ValidationError as exc:
            error = exc.errors()[0]
            location = ".".join(str(part) for part in error.get("loc", ()))
            message = error.get("msg", "invalid provider configuration")
            raise ConfigError(f"Publication {publication} provider {self.id} {location}: {message}".strip()) from exc
        return config.model_dump(mode="python", exclude_none=True)

    def resolve_target(
        self,
        release: ReleaseMetadata,
        target: ResolvedPublishTarget,
        unresolved_platforms: dict[str, ArtifactPlatformSpec],
        resolver: VersionSourceResolver,
    ) -> None:
        del release
        for platform in target.selected_platforms:
            unresolved_platform = unresolved_platforms[platform]
            resolved_platform = target.artifact.platforms[platform]
            if resolved_platform.platform_versions:
                continue
            source = unresolved_platform.platform_versions_source or resolver.default_sources["platform_versions"]
            raw_versions = resolver.resolve_latest(source, "platform_versions")
            resolved_platform.platform_versions = [self.mapper.map(platform, value) for value in raw_versions]

    def build_publisher(self, credentials: str) -> HangarPublisher:
        return HangarPublisher(credentials)
