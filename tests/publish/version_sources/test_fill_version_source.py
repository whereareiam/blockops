from publish.version_sources.type.fill import PaperMcFillProjectVersionSource


def test_fill_version_source_returns_first_available_version(monkeypatch) -> None:
    source = PaperMcFillProjectVersionSource()
    monkeypatch.setattr(
        source,
        "_get_fill_project",
        lambda project: {"versions": {"26.1": ["26.1.2"], "26.0": ["26.0.1"]}},
    )

    result = source.resolve_latest(
        {
            "type": "papermc-fill-project",
            "project": "paper",
        },
        "game_versions",
    )

    assert result == ["26.1.2"]
