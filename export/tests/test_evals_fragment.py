"""patches/repo-settings/evals_fragment.py: skills-evals' element moves out of
fleet.yml into the fragment, structurally (DECISIONS C13).

Invented fleets only. Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

EXPORT_DIR = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "kit_patch_evals_fragment", EXPORT_DIR / "patches" / "repo-settings" / "evals_fragment.py")
frag = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(frag)

FLEET = """\
# A header comment the cut keeps.
defaults:
  merge: {merge_commit: true}

repos:
  # A comment about the list, kept in fleet.yml.
  - name: acme-example/one
    manage: ["all"]
  # A comment above skills-evals, about several repos: kept in fleet.yml.
  - name: acme-example/skills-evals
    manage: ["all"]
    overrides:
      # why: a comment inside the element moves with it.
      labels:
        - name: eval-scaffold
          color: C5DEF5
      extra_rulesets:
        - name: persistent branches
          target_branches: ["persistent/**"]
          rules: [deletion]
  # --- a comment that belongs to the next element ---
  - name: acme-example/two
    manage: []
"""


def test_the_element_moves_with_its_comments():
    rest, fragment = frag.split(FLEET)
    assert [r["name"] for r in yaml.safe_load(rest)["repos"]] == ["acme-example/one", "acme-example/two"]
    assert yaml.safe_load(fragment)["repos"] == [r for r in yaml.safe_load(FLEET)["repos"] if r["name"].endswith("/skills-evals")]
    assert "# why: a comment inside the element moves with it." in fragment
    assert "# why: a comment inside" not in rest
    for kept in ("# A header comment the cut keeps.", "# A comment above skills-evals, about several repos",
                 "# --- a comment that belongs to the next element ---"):
        assert kept in rest and kept not in fragment
    # The lines are moved unchanged: the two files hold every line of the source.
    assert sorted(rest.splitlines() + fragment[len(frag.HEADER):].splitlines()[1:]) == sorted(FLEET.splitlines())


def test_the_fragment_starts_with_its_header():
    _, fragment = frag.split(FLEET)
    assert fragment.startswith(frag.HEADER + "repos:\n  - name: acme-example/skills-evals\n")


def test_the_last_element_moves_too():
    text = FLEET.replace("  # --- a comment that belongs to the next element ---\n  - name: acme-example/two\n    manage: []\n", "")
    rest, fragment = frag.split(text)
    assert [r["name"] for r in yaml.safe_load(rest)["repos"]] == ["acme-example/one"]
    assert yaml.safe_load(fragment)["repos"][0]["overrides"]["extra_rulesets"][0]["rules"] == ["deletion"]


def test_a_missing_element_fails_the_export():
    # The negative control: a re-sync whose fleet.yml lost the element.
    text = FLEET.replace("acme-example/skills-evals", "acme-example/three")
    with pytest.raises(SystemExit, match="expected exactly 1 .* found 0"):
        frag.split(text)


def test_a_doubled_element_fails_the_export():
    text = FLEET.replace("  - name: acme-example/two\n", "  - name: acme-example/skills-evals\n")
    with pytest.raises(SystemExit, match="found 2"):
        frag.split(text)


def test_a_name_that_only_mentions_the_repo_does_not_count():
    # Found by its parsed name, not by text: a comment or a longer name is not it.
    text = FLEET.replace("acme-example/skills-evals", "acme-example/skills-evals-archive")
    with pytest.raises(SystemExit, match="found 0"):
        frag.split(text)


def test_a_fleet_without_a_repos_list_fails():
    with pytest.raises(SystemExit, match="no single block `repos:` list"):
        frag.split("defaults: {}\n")
