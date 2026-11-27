"""The owner's vendor notes ship empty (acsi-kit, after PR #139's real walk).

docs/reference/agent-<agent>.DISCREPANCIES.md and
docs/reference/vendor-issue-drafts/ hold the source owner's own findings on
Claude Code and Codex. Merging the starter pull request ran
vendor-discrepancy-alert.yml on them, which opened one "Vendor discrepancy" or
"Vendor issue draft ready" issue per entry in the adopter's repo: the owner's
follow-ups, not the adopter's. So:

- each DISCREPANCIES.md keeps everything up to and including its
  `## Entries` heading (the title, "How to add an entry" and the fenced entry
  template, which the alert script never reads as an entry) and says there are
  none yet;
- every draft under vendor-issue-drafts/ is removed, and a README.md (which
  the alert script skips by name) says what goes there, so the folder the
  process doc names still exists;
- a link elsewhere into one of those files' entries loses its anchor (the
  entry is gone; the file is still there), and a link to a removed draft is
  an error;
- test-discrepancy-alert.js's two "regression — the real ..." tests, which
  asserted the owner's entries, become one test that the shipped files keep
  their `## Entries` heading and template and parse to no entries.

Runs on the substituted tree. Every step names what it expected when the
source moves under it.
"""

from __future__ import annotations

import re
from pathlib import Path

REF = Path("docs") / "reference"
DRAFTS = REF / "vendor-issue-drafts"
TEST = Path("test") / "test-discrepancy-alert.js"

NONE_YET = (
    "\nNone yet. Add the first one at the top of this section, in the format "
    "above.\n"
)

DRAFTS_README = """# Vendor issue drafts

One folder per agent (`claude-code/`, `codex/`), one file per draft:
`<agent>/YYYY-MM-DD-<slug>.md`, written in step 3 of
[`agent-discrepancy-process.md`](../agent-discrepancy-process.md). Merging a
new draft opens a "Vendor issue draft ready" issue in this repo
(`vendor-discrepancy-alert.yml`); this README is skipped.

The adoption kit ships no drafts: the ones in the source repo were its
owner's.
"""

REGRESSION_START = 'test("parseEntries: regression — the real agent-'

SHIPPED_TEST = '''test("parseEntries: the shipped DISCREPANCIES.md files keep their template and hold no entries yet", () => {
  for (const agent of ["claude-code", "codex"]) {
    const p = path.join(__dirname, "..", "docs", "reference", `agent-${agent}.DISCREPANCIES.md`);
    const text = fs.readFileSync(p, "utf8");
    assert.ok(text.includes("\\n## Entries\\n"), `${agent}: keeps its Entries heading`);
    assert.ok(text.includes("### YYYY-MM-DD — "), `${agent}: keeps its entry template`);
    assert.deepEqual(parseEntries(text), [], `${agent}: the template is not an entry, and there are none`);
  }
});
'''

# A markdown link target into a DISCREPANCIES.md file, with an anchor.
_ANCHORED = re.compile(r"(\]\((?:[^()\s]*/)?agent-[a-z0-9-]+\.DISCREPANCIES\.md)#[^)\s]+\)")
_DRAFT_LINK = re.compile(r"\]\((?:[^()\s]*/)?vendor-issue-drafts/[a-z0-9-]+/[^)\s<>]+\.md\)")


def _empty_entries(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    at = [i for i, ln in enumerate(lines) if ln.rstrip("\n") == "## Entries"]
    if len(at) != 1:
        raise SystemExit(f"vendor_notes: {path.name}: expected one '## Entries' line, found {len(at)}")
    path.write_text("".join(lines[: at[0] + 1]) + NONE_YET, encoding="utf-8")


def _replace_regression_tests(text: str) -> str:
    lines = text.splitlines(keepends=True)
    starts = [i for i, ln in enumerate(lines) if ln.startswith(REGRESSION_START)]
    if len(starts) != 2:
        raise SystemExit(f"vendor_notes: {TEST}: expected 2 regression tests on the real files, found {len(starts)}")
    spans = []
    for s in starts:
        end = next((j for j in range(s + 1, len(lines)) if lines[j] == "});\n"), None)
        if end is None:
            raise SystemExit(f"vendor_notes: {TEST}: no closing '}});' line after line {s + 1}")
        spans.append((s, end + 1))
    (s1, e1), (s2, e2) = spans
    between = "".join(lines[e1:s2])
    if between.strip():
        raise SystemExit(f"vendor_notes: {TEST}: the two regression tests are no longer adjacent")
    return "".join(lines[:s1]) + SHIPPED_TEST + "".join(lines[e2:])


def apply(root: Path, ctx) -> None:
    notes = sorted((root / REF).glob("agent-*.DISCREPANCIES.md"))
    if not notes:
        raise SystemExit("vendor_notes: no docs/reference/agent-*.DISCREPANCIES.md")
    for path in notes:
        _empty_entries(path)

    drafts = root / DRAFTS
    if drafts.is_dir():
        for f in sorted(drafts.rglob("*"), reverse=True):
            if f.is_dir():
                f.rmdir()
            else:
                f.unlink()
    drafts.mkdir(parents=True, exist_ok=True)
    (drafts / "README.md").write_text(DRAFTS_README, encoding="utf-8")

    for md in sorted(root.rglob("*.md")):
        if md.is_symlink() or "node_modules" in md.parts:
            continue
        text = md.read_text(encoding="utf-8")
        new = _ANCHORED.sub(r"\1)", text)
        rel = md.relative_to(root)
        if _DRAFT_LINK.search(new):
            raise SystemExit(f"vendor_notes: {rel} links a vendor issue draft the kit does not ship")
        if new != text:
            md.write_text(new, encoding="utf-8")

    test = root / TEST
    test.write_text(_replace_regression_tests(test.read_text(encoding="utf-8")), encoding="utf-8")
