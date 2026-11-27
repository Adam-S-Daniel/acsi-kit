"""patches/_agent-guidance/vendor_notes.py: the owner's vendor notes ship empty.

Run: python3 -m pytest KIT/export/tests -q
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

EXPORT_DIR = Path(__file__).resolve().parents[1]
KIT = EXPORT_DIR.parent
STARTER = KIT / "starter" / "agent-guidance"
_spec = importlib.util.spec_from_file_location(
    "kit_patch_vendor_notes", EXPORT_DIR / "patches" / "_agent-guidance" / "vendor_notes.py")
vendor_notes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vendor_notes)

NOTES = """# Discrepancies — X

## How to add an entry

```markdown
### YYYY-MM-DD — <one-line summary>

- **Vendor proposal:** `draft: [<file>](vendor-issue-drafts/x/<file>.md)`
```

## Entries

### 2026-01-01 — The owner's finding

- **Vendor proposal:** draft: [a.md](vendor-issue-drafts/x/a.md)
"""

TEST_JS = """const x = 1;

test("parseEntries: regression — the real agent-x.DISCREPANCIES.md parses", () => {
  owner();
});

test("parseEntries: regression — the real agent-y.DISCREPANCIES.md contains", () => {
  owner();
});

// ── 2. newEntries
"""


def tree(tmp_path: Path, notes: str = NOTES, test_js: str = TEST_JS) -> Path:
    ref = tmp_path / "docs" / "reference"
    (ref / "vendor-issue-drafts" / "x").mkdir(parents=True)
    (ref / "agent-x.DISCREPANCIES.md").write_text(notes, encoding="utf-8")
    (ref / "vendor-issue-drafts" / "x" / "a.md").write_text("# Draft\n", encoding="utf-8")
    (tmp_path / "docs" / "evidence").mkdir()
    (tmp_path / "docs" / "evidence" / "e.md").write_text(
        "See [it](../reference/agent-x.DISCREPANCIES.md#2026-01-01--the-owners-finding) and "
        "[the file](../reference/agent-x.DISCREPANCIES.md).\n", encoding="utf-8")
    (tmp_path / "test").mkdir()
    (tmp_path / "test" / "test-discrepancy-alert.js").write_text(test_js, encoding="utf-8")
    return tmp_path


def test_entries_go_and_the_template_stays(tmp_path):
    root = tree(tmp_path)
    vendor_notes.apply(root, {})
    text = (root / "docs/reference/agent-x.DISCREPANCIES.md").read_text()
    assert text.startswith(NOTES.split("### 2026-01-01")[0].rstrip("\n") + "\n")
    assert "### YYYY-MM-DD" in text
    assert "2026-01-01" not in text and "owner's finding" not in text
    assert text.endswith("## Entries\n" + vendor_notes.NONE_YET)


def test_drafts_go_and_a_readme_stays(tmp_path):
    root = tree(tmp_path)
    vendor_notes.apply(root, {})
    drafts = root / "docs/reference/vendor-issue-drafts"
    assert sorted(p.relative_to(drafts).as_posix() for p in drafts.rglob("*")) == ["README.md"]


def test_an_anchor_into_a_gone_entry_is_dropped(tmp_path):
    root = tree(tmp_path)
    vendor_notes.apply(root, {})
    assert (root / "docs/evidence/e.md").read_text() == (
        "See [it](../reference/agent-x.DISCREPANCIES.md) and "
        "[the file](../reference/agent-x.DISCREPANCIES.md).\n")


def test_a_link_to_a_removed_draft_is_an_error(tmp_path):
    root = tree(tmp_path)
    (root / "docs/evidence/d.md").write_text("[d](../reference/vendor-issue-drafts/x/a.md)\n")
    with pytest.raises(SystemExit, match="links a vendor issue draft"):
        vendor_notes.apply(root, {})


def test_the_owner_entry_tests_become_one_empty_file_test(tmp_path):
    root = tree(tmp_path)
    vendor_notes.apply(root, {})
    js = (root / "test/test-discrepancy-alert.js").read_text()
    assert "owner()" not in js
    assert js == "const x = 1;\n\n" + vendor_notes.SHIPPED_TEST + "\n// ── 2. newEntries\n"


@pytest.mark.parametrize("notes, why", [
    (NOTES.replace("## Entries\n", ""), "expected one '## Entries' line, found 0"),
    (NOTES + "\n## Entries\n", "expected one '## Entries' line, found 2"),
])
def test_an_unexpected_notes_shape_stops_the_export(tmp_path, notes, why):
    with pytest.raises(SystemExit, match=why):
        vendor_notes.apply(tree(tmp_path, notes=notes), {})


def test_a_moved_test_stops_the_export(tmp_path):
    js = TEST_JS.replace('test("parseEntries: regression — the real agent-y', 'test("other')
    with pytest.raises(SystemExit, match="expected 2 regression tests"):
        vendor_notes.apply(tree(tmp_path, test_js=js), {})


def test_the_committed_starter_ships_no_owner_notes():
    ref = STARTER / "docs" / "reference"
    notes = sorted(ref.glob("agent-*.DISCREPANCIES.md"))
    assert len(notes) >= 2
    for path in notes:
        text = path.read_text(encoding="utf-8")
        tail = text.split("\n## Entries\n", 1)[1]
        assert tail == vendor_notes.NONE_YET, path.name
    drafts = ref / "vendor-issue-drafts"
    assert [p.name for p in drafts.rglob("*")] == ["README.md"]
