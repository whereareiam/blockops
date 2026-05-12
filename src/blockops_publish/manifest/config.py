from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
import yaml

from blockops_publish.publish.models import (
    ArtifactPlatformSpec,
    ArtifactSpec,
    DistributionManifest,
    PublicationSpec,
)


class ConfigError(ValueError):
    """Raised when the distribution configuration is invalid."""


class ArtifactPlatformModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loaders: list[str] = Field(default_factory=list)
    game_versions: list[str] = Field(default_factory=list)
    platform_versions: list[str] = Field(default_factory=list)
    game_versions_source: dict[str, Any] | None = None
    platform_versions_source: dict[str, Any] | None = None


class ArtifactModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    file: str
    platform: str | None = None
    platforms: dict[str, ArtifactPlatformModel] | None = None
    loaders: list[str] = Field(default_factory=list)
    game_versions: list[str] = Field(default_factory=list)
    platform_versions: list[str] = Field(default_factory=list)
    game_versions_source: dict[str, Any] | None = None
    platform_versions_source: dict[str, Any] | None = None

    @field_validator("file")
    @classmethod
    def validate_file(cls, value: str) -> str:
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, value: str | None) -> str | None:
        if value == "":
            raise ValueError("must not be empty when defined")
        return value

    @field_validator("game_versions_source", "platform_versions_source")
    @classmethod
    def validate_source(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None and not isinstance(value, dict):
            raise ValueError("must be a mapping when defined")
        return value

    def expand_platforms(self) -> dict[str, ArtifactPlatformModel]:
        if self.platforms is not None:
            return self.platforms
        if not self.platform:
            raise ValueError("must define platform or platforms")
        return {
            self.platform: ArtifactPlatformModel(
                loaders=self.loaders,
                game_versions=self.game_versions,
                platform_versions=self.platform_versions,
                game_versions_source=self.game_versions_source,
                platform_versions_source=self.platform_versions_source,
            )
        }


class ProviderReferenceModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not value:
            raise ValueError("must not be empty")
        return value


class PublicationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: ProviderReferenceModel
    artifact: str
    platforms: list[str] | None = None

    @field_validator("artifact")
    @classmethod
    def validate_artifact(cls, value: str) -> str:
        if not value:
            raise ValueError("must not be empty")
        return value


class ReleaseClassificationRuleModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: str
    patterns: list[str]

    @field_validator("phase")
    @classmethod
    def validate_phase(cls, value: str) -> str:
        if value not in {"release", "beta", "alpha"}:
            raise ValueError("must be one of release, beta, alpha")
        return value

    @field_validator("patterns")
    @classmethod
    def validate_patterns(cls, value: list[str]) -> list[str]:
        if not value or not all(isinstance(pattern, str) and pattern for pattern in value):
            raise ValueError("must be a non-empty list of strings")
        return value


class ReleaseClassificationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rules: list[ReleaseClassificationRuleModel] = Field(default_factory=list)
    default_phase: str = "release"

    @field_validator("default_phase")
    @classmethod
    def validate_default_phase(cls, value: str) -> str:
        if value not in {"release", "beta", "alpha"}:
            raise ValueError("must be one of release, beta, alpha")
        return value


class ReleaseConfigModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    classification: ReleaseClassificationModel | None = None


class ManifestModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    release: ReleaseConfigModel | None = None
    artifacts: dict[str, ArtifactModel]
    publications: dict[str, PublicationModel]

    @field_validator("artifacts", "publications")
    @classmethod
    def validate_non_empty_mapping(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("must be a non-empty mapping")
        return value


def load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"Manifest file does not exist: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ConfigError(f"Expected a mapping in manifest: {path}")

    return data


def load_override_file(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}

    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return {}

    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ConfigError("Override YAML must be a mapping at the top level")

    return data


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = deep_merge(current, value)
        else:
            merged[key] = deepcopy(value)
    return merged


def validate_manifest(manifest: dict[str, Any]) -> None:
    _parse_manifest_model(manifest)


def parse_manifest(manifest: dict[str, Any]) -> DistributionManifest:
    parsed = _parse_manifest_model(manifest)

    artifacts: dict[str, ArtifactSpec] = {}
    for artifact_name, artifact_model in parsed.artifacts.items():
        platforms = artifact_model.expand_platforms()
        artifacts[artifact_name] = ArtifactSpec(
            name=artifact_name,
            file_template=artifact_model.file,
            platforms={
                platform_key: ArtifactPlatformSpec(
                    key=platform_key,
                    loaders=list(platform_spec.loaders),
                    game_versions=list(platform_spec.game_versions),
                    platform_versions=list(platform_spec.platform_versions),
                    game_versions_source=platform_spec.game_versions_source,
                    platform_versions_source=platform_spec.platform_versions_source,
                )
                for platform_key, platform_spec in platforms.items()
            },
        )

    publications: dict[str, PublicationSpec] = {}
    for publication_name, publication_model in parsed.publications.items():
        provider = publication_model.provider.model_dump(mode="python")
        publications[publication_name] = PublicationSpec(
            provider_id=publication_model.provider.id,
            publication=publication_name,
            artifact_name=publication_model.artifact,
            platforms=list(publication_model.platforms) if publication_model.platforms is not None else None,
            provider=provider,
        )

    for publication_name, publication in publications.items():
        if publication.artifact_name not in artifacts:
            raise ConfigError(f"Publication {publication_name} references unknown artifact {publication.artifact_name}")

    return DistributionManifest(artifacts=artifacts, publications=publications)


def _parse_manifest_model(manifest: dict[str, Any]) -> ManifestModel:
    try:
        return ManifestModel.model_validate(manifest)
    except ValidationError as exc:
        error = exc.errors()[0]
        location = ".".join(str(part) for part in error.get("loc", ()))
        message = error.get("msg", "invalid manifest")
        if location:
            raise ConfigError(f"{location}: {message}") from exc
        raise ConfigError(message) from exc
