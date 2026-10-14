import pytest

from publish.manifest.config import ConfigError
from publish.providers.modrinth.provider import ModrinthProvider


def _parse(provider_data: dict) -> dict:
    return ModrinthProvider().parse_provider("provider-modrinth", {"id": "modrinth", "project_id": "abc", **provider_data})


def test_modrinth_provider_accepts_loader_fields() -> None:
    parsed = _parse({"loader_fields": {"environment": "server_only", "mrpack_loaders": ["fabric"], "flag": True}})

    assert parsed["loader_fields"] == {"environment": "server_only", "mrpack_loaders": ["fabric"], "flag": True}


def test_modrinth_provider_defaults_to_no_loader_fields() -> None:
    assert _parse({})["loader_fields"] == {}


@pytest.mark.parametrize("field", ["loaders", "game_versions", "version_number", "primary_file"])
def test_modrinth_provider_rejects_loader_fields_that_replace_version_data(field: str) -> None:
    with pytest.raises(ConfigError, match=f"{field} is set by the publisher"):
        _parse({"loader_fields": {field: "value"}})


@pytest.mark.parametrize("value", ["", [], None, {"nested": "value"}])
def test_modrinth_provider_rejects_empty_or_structured_loader_field_values(value: object) -> None:
    with pytest.raises(ConfigError, match="loader_fields"):
        _parse({"loader_fields": {"environment": value}})
