"""The shipped Pester tests carry no guard that tells the owner's names apart by letter case.

wsl-automation's tests/AgentWorkspaceTrust.Tests.ps1 had a guard that banned
the source owner's lowercase clone-folder names in src/ and told them from the
owner's capitalized GitHub URLs by case. The kit's substitutions turn both into
the same lowercase placeholder, so the shipped guard failed on src/'s own
github.com URLs (re-pin round 23 in export/DECISIONS.md cuts it).

What this does: a plain text search of the shipped *.Tests.ps1 files under
starter/wsl-automation/tests for the cut block's title, and for a string
literal that starts with a slash or backslash before a placeholder owner name
(the shape of that guard's banned list). What it does not cover: a banned
list written another way (a variable, a here-string, a regex, a name without
a leading separator), a case-dependent assertion in another language or tree,
or the adopter's own names after copy-starter.sh replaces the placeholders.
"""

from __future__ import annotations

import re
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent.parent
TESTS = KIT / "starter" / "wsl-automation" / "tests"
PLACEHOLDERS = ("example-adopter",)  # also matches example-adopter-two
BANNED_LITERAL = re.compile(r"""['"][\\/]+(?:%s)""" % "|".join(map(re.escape, PLACEHOLDERS)))


def pester_files() -> list[Path]:
    return sorted(TESTS.glob("*.Tests.ps1"))


def test_the_folder_name_guard_is_not_shipped():
    text = (TESTS / "AgentWorkspaceTrust.Tests.ps1").read_text(encoding="utf-8")
    assert "Describe 'No owner-specific folder names in src'" not in text


def test_no_shipped_pester_file_bans_a_placeholder_name_by_literal():
    assert pester_files(), f"no *.Tests.ps1 under {TESTS}"
    hits = [f"{p.relative_to(KIT)}:{n}"
            for p in pester_files()
            for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1)
            if BANNED_LITERAL.search(line)]
    assert not hits, "a Pester file names a placeholder owner in a separator-led literal: " + ", ".join(hits)


def test_the_literal_search_finds_the_cut_guards_shape():
    # Negative control: the banned list as it ships before the cut.
    assert BANNED_LITERAL.search("$banned = @('C:\\repos', '\\example-adopter', '/example-adopter-two')")
    assert not BANNED_LITERAL.search("'https://github.com/example-adopter/x'")
