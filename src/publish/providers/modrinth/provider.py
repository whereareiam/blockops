from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from publish.manifest.config import ConfigError
from publish.providers.base import ProviderDefinition
from publish.providers.modrinth.publisher import ModrinthPublisher
from publish.models import ArtifactPlatformSpec, ReleaseMetadata, ResolvedPublishTarget
from publish.version_sources.resolver import VersionSourceResolver


class ModrinthDependencyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dependency_type: Literal["required", "optional", "incompatible", "embedded"]
    project_id: str | None = None
    version_id: str | None = None
    file_name: str | None = None

    @model_validator(mode="after")
    def validate_target(self) -> "ModrinthDependencyModel":
        if any(isinstance(value, str) and value for value in (self.project_id, self.version_id, self.file_name)):
            return self
        raise ValueError("must define project_id, version_id, or file_name")


LoaderFieldScalar = str | int | bool
LoaderFieldValue = LoaderFieldScalar | list[LoaderFieldScalar]

# Keys of the create version payload that the publisher sets itself, or that Modrinth reads as
# version data instead of loader fields. A loader field must not replace them.
RESERVED_PAYLOAD_KEYS = frozenset(
    {
        "name",
        "version_title",
        "version_number",
        "changelog",
        "version_body",
        "dependencies",
        "game_versions",
        "version_type",
        "release_channel",
        "loaders",
        "featured",
        "status",
        "project_id",
        "mod_id",
        "file_parts",
        "primary_file",
        "file_types",
        "uploaded_images",
        "ordering",
    }
)


class ModrinthReclassifyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loaders: list[str] | None = None
    version_type: str | None = None
    status: str | None = None


class ModrinthProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Literal["modrinth"]
    project_id: str
    dependencies: list[ModrinthDependencyModel] = Field(default_factory=list)
    upload_loaders: list[str] | None = None
    loader_fields: dict[str, LoaderFieldValue] = Field(default_factory=dict)
    reclassify: ModrinthReclassifyModel | None = None
    release_type_map: dict[str, str] = Field(
        default_factory=lambda: {
            "release": "release",
            "beta": "beta",
            "alpha": "alpha",
        }
    )

    @field_validator("loader_fields")
    @classmethod
    def validate_loader_fields(cls, value: dict[str, LoaderFieldValue]) -> dict[str, LoaderFieldValue]:
        for key, field_value in value.items():
            if not key:
                raise ValueError("field names must not be empty")
            if key in RESERVED_PAYLOAD_KEYS:
                raise ValueError(f"{key} is set by the publisher and cannot be a loader field")
            if field_value == "" or field_value == []:
                raise ValueError(f"{key} must not be empty")
        return value


class ModrinthProvider(ProviderDefinition):
    id = "modrinth"
    config_model = ModrinthProviderConfig

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
            if resolved_platform.game_versions:
                continue
            source = unresolved_platform.game_versions_source or resolver.default_sources["game_versions"]
            resolved_platform.game_versions = resolver.resolve_latest(source, "game_versions")

    def build_publisher(self, credentials: str) -> ModrinthPublisher:
        return ModrinthPublisher(credentials)
