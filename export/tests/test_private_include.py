"""The private source ships only the files its manifest's `include` names.

An `exclude` list lets a file the private source adds later through to the
public kit; an `include` list does not (DECISIONS, re-pin round 21).

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

EXPORT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPORT_DIR))
import export  # noqa: E402


def _tree(*paths):
    return {p: object() for p in paths}


def test_the_private_manifest_has_an_include_list():
    manifest = export.load_manifests()["agentskills-private"]
    assert manifest.get("include"), "agentskills-private must list the files it ships"


def test_a_file_not_listed_is_dropped():
    tree = _tree("README.md", "docs/new-private-notes.md")
    export._apply_include("x", {"include": ["README.md"]}, tree)
    assert list(tree) == ["README.md"]


def test_no_include_key_keeps_everything():
    tree = _tree("README.md", "docs/a.md")
    export._apply_include("x", {}, tree)
    assert sorted(tree) == ["README.md", "docs/a.md"]


def test_a_listed_file_missing_at_the_pin_fails():
    with pytest.raises(export.ExportError, match="not in the source"):
        export._apply_include("x", {"include": ["README.md", "gone.md"]}, _tree("README.md"))


@pytest.mark.parametrize("entry", ["docs/*", "docs/", "docs/?.md", "[ab].md"])
def test_patterns_and_folders_are_refused(entry):
    with pytest.raises(export.ExportError, match="exact file paths"):
        export._apply_include("x", {"include": [entry]}, _tree("docs/a.md"))


def test_an_empty_include_is_refused():
    with pytest.raises(export.ExportError, match="non-empty"):
        export._apply_include("x", {"include": []}, _tree("README.md"))
