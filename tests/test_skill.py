"""Tests for .claude/skills/consent-audit/SKILL.md — the Claude Code skill.

Skill files are markdown with YAML frontmatter. The frontmatter is the
trigger contract: Claude Code reads `name` + `description` to decide whether
to invoke the skill. If either is missing or stale, the skill silently never
fires. These tests catch that.

Also verifies the skill body doesn't reference removed subcommands (the
`consent-engine chat` subcommand was removed in v0.5.0 — the skill must not
still tell users to invoke it).
"""

from __future__ import annotations

from pathlib import Path

import pytest

SKILL_PATH = Path(__file__).parent.parent / ".claude" / "skills" / "consent-audit" / "SKILL.md"


def test_skill_file_exists() -> None:
    assert SKILL_PATH.exists(), f"SKILL.md missing at {SKILL_PATH}"


def test_skill_has_yaml_frontmatter() -> None:
    """First line must be `---` and frontmatter must contain name + description."""
    text = SKILL_PATH.read_text()
    assert text.startswith("---"), "SKILL.md must open with YAML frontmatter (---)"
    end = text.index("---", 3)
    frontmatter = text[3:end]
    assert "name:" in frontmatter
    assert "description:" in frontmatter


def test_skill_name_matches_directory() -> None:
    text = SKILL_PATH.read_text()
    end = text.index("---", 3)
    frontmatter = text[3:end]
    # crude YAML read to avoid an extra dependency in the test deps
    name_line = next(line for line in frontmatter.splitlines() if line.strip().startswith("name:"))
    name = name_line.split(":", 1)[1].strip()
    assert name == "consent-audit"


def test_skill_description_mentions_consent_keywords() -> None:
    """The skill triggers on the description text. It must include the words a user would naturally type."""
    text = SKILL_PATH.read_text()
    end = text.index("---", 3)
    frontmatter_lower = text[3:end].lower()
    for keyword in ("audit", "consent", "url"):
        assert keyword in frontmatter_lower, f"description must include '{keyword}'"


def test_skill_does_not_reference_removed_chat_subcommand() -> None:
    """The `consent-engine chat <audit_id>` subcommand was removed in v0.5.0.
    The skill must not still point users at it.
    """
    text = SKILL_PATH.read_text()
    assert "consent-engine chat" not in text, (
        "SKILL.md references the removed `consent-engine chat` subcommand. "
        "Remove or replace with `query_evidence` via MCP."
    )


def test_skill_run_command_is_current() -> None:
    """The skill should show `uvx consent-engine audit <url>` as the run command."""
    text = SKILL_PATH.read_text()
    assert "consent-engine audit" in text


@pytest.mark.parametrize(
    "removed_token",
    [
        "from consent_engine.llm.client import chat_with_context",  # removed in v0.5.0
        "--with-gpc ",  # deprecated-but-tolerated flag (always on now); skill should be clean
    ],
)
def test_skill_does_not_reference_dead_code(removed_token: str) -> None:
    text = SKILL_PATH.read_text()
    assert removed_token not in text
