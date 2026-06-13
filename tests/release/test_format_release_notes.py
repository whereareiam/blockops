import pytest

from release.notes import format_release_notes


def test_format_release_notes_builds_bbcode() -> None:
    release_body = """# Update 2.2.0 - Packed for Everyone

Identica now ships as a universal plugin jar, simplifying installation and platform support.

# Changelog

## What’s new

* Platform: Introduce universal plugin jar in [#76](https://github.com/whereareiam/Identica/pull/76)

# Support

If you need help, join us on [Discord](https://discord.arcadeya.com).
"""

    assert format_release_notes(release_body, "bbcode") == """[SIZE=6][B]Update 2.2.0 - Packed for Everyone[/B][/SIZE]

Identica now ships as a universal plugin jar, simplifying installation and platform support.

[SIZE=6][B]Changelog[/B][/SIZE]

[SIZE=5][B]What’s new[/B][/SIZE]

[LIST]
[*]Platform: Introduce universal plugin jar in [URL='https://github.com/whereareiam/Identica/pull/76']#76[/URL]
[/LIST]

[SIZE=6][B]Support[/B][/SIZE]

If you need help, join us on [URL='https://discord.arcadeya.com']Discord[/URL].
"""


def test_format_release_notes_groups_markdown_by_prefix() -> None:
    release_body = """# Update 2.3.0 - [Short subtitle]

[1-2 sentence summary of the release.]

# Changelog

* API: Introduce scenario events in [#89](https://github.com/whereareiam/Identica/pull/89)
* Configuration: Improve config file structure in [#100](https://github.com/whereareiam/Identica/pull/100)
* API: Optimize event listener dispatch in [#101](https://github.com/whereareiam/Identica/pull/101)

# Support

Support text
"""

    assert format_release_notes(release_body, "markdown", "title-prefix") == """# Update 2.3.0 - [Short subtitle]

[1-2 sentence summary of the release.]

# Changelog

## API

* Introduce scenario events in [#89](https://github.com/whereareiam/Identica/pull/89)
* Optimize event listener dispatch in [#101](https://github.com/whereareiam/Identica/pull/101)

## Configuration

* Improve config file structure in [#100](https://github.com/whereareiam/Identica/pull/100)

# Support

Support text
"""


def test_format_release_notes_rejects_unknown_format() -> None:
    with pytest.raises(ValueError, match="Unsupported release note format: unknown"):
        format_release_notes("# Title", "unknown")


def test_format_release_notes_rejects_unknown_grouping() -> None:
    with pytest.raises(ValueError, match="Unsupported release note grouping: unknown"):
        format_release_notes("# Title", "markdown", "unknown")
