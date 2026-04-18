from blockops_publish.metadata import classify_version, derive_release_title, trim_release_body


def test_derive_release_title_with_en_dash() -> None:
    body = "# Update 2.0.0-RC6 – Breaking Changes\n\nBody"
    assert derive_release_title(body, "Fallback") == "Breaking Changes"


def test_derive_release_title_with_plain_dash() -> None:
    body = "# Update 2.0.0-RC6 - Breaking Changes\n\nBody"
    assert derive_release_title(body, "Fallback") == "Breaking Changes"


def test_derive_release_title_without_heading_uses_fallback() -> None:
    assert derive_release_title("No heading", "Fallback") == "Fallback"


def test_trim_release_body_removes_first_heading_and_blank_lines() -> None:
    body = "# Update 2.0.0-RC6 – Breaking Changes\n\nFirst paragraph\n\nSecond paragraph"
    assert trim_release_body(body) == "First paragraph\n\nSecond paragraph"


def test_trim_release_body_returns_empty_for_heading_only() -> None:
    body = "# Update 2.0.0-RC6 – Breaking Changes\n\n"
    assert trim_release_body(body) == ""


def test_classify_version() -> None:
    assert classify_version("2.0.0") == "release"
    assert classify_version("2.0.0-beta1") == "beta"
    assert classify_version("2.0.0-RC6") == "beta"
    assert classify_version("2.0.0-alpha1") == "alpha"
