"""DECISIONS C11 and "Kit-only blocks": the kit's own re-sync merge rule and `kit_resync` key do not ship.

The source's fleet-worker spec may carry blocks that tell the owner's fleet
worker it may merge the kit's re-sync pull requests (heads `resync/auto` and
`resync-fix/*`), and `repos.yml` may carry a top-level `kit_resync` key. An
adopter's fleet has no kit, so neither belongs in what the kit ships:

* in every Markdown file under `docs/routines/`, each region from a line that is
  exactly `<!-- kit-only:begin -->` through the matching line that is exactly
  `<!-- kit-only:end -->` is cut, plus one blank line after the end marker, so
  the paragraphs around it stay one blank line apart;
* in `repos.yml`, the top-level `kit_resync` key, its body and the comment
  block directly above it are cut, plus one blank line after it.

The rule's decision record and its test do not ship either (DECISIONS "Kit-only
blocks", second part):

* `docs/decisions/0051-...` (the ADR that adopts the rule, the source fleet's
  story of the kit) is deleted, with its row in `docs/decisions/README.md` and
  the "Widened by [0051]..." sentence in ADR 0041's status line; any other
  file still naming the ADR's file stops the export, so nothing dangles;
* in `test/test-prompt-audit-sweep.js`, the test that asserts the block, the
  key and the ADR is cut, with the five `mutations` entries whose anchors sit
  inside the block, and the count `test/run-tests.sh` expects from that file
  goes down by one.

The patch landed before the source change, so it is tolerant: a file without
markers, a `repos.yml` without the key, or a tree without ADR 0051 or its test
is left byte for byte as it is. A marker that is unbalanced, nested or out of
order stops the export, naming the file, rather than shipping half a block.
Runs on the substituted tree, before the other patches, so the marker text is
intact.
"""

from __future__ import annotations

import re
from pathlib import Path

BEGIN = "<!-- kit-only:begin -->"
END = "<!-- kit-only:end -->"
KEY = "kit_resync:"

ADR = "0051-the-fleet-worker-merges-the-kits-re-sync-pull-requests.md"
ADR_0041 = "docs/decisions/0041-the-fleet-worker-merges-reviewed-agent-made-changes.md"
# The status-line sentence that points at the ADR, up to its closing period.
WIDENED = re.compile(r" ?Widened by \[0051\]\(" + re.escape(ADR) + r"\)[^\n]*?\.(?=[ \n]|$)")
SWEEP_TEST = "test/test-prompt-audit-sweep.js"
TEST_TITLE = "test(\"fleet worker merges the kit's re-sync pull requests, named only in repos.yml (ADR 0051)\", () => {\n"
KIT_MUTATIONS = ("kitauthor", "kitconfig", "kitprivate", "kitpins", "kitmarker")
RUN_TESTS = "test/run-tests.sh"
# The three places test_prompt_audit_sweep() states the pass count.
COUNT_FORMS = ('"$pass_n" == "{n}"', 'prompt-audit sweep policy: {n} passed"', "need rc=0, pass={n}, fail=0")


def strip_blocks(text: str, where: str) -> str:
    """Cut every begin..end region (and one blank line after it)."""
    out: list[str] = []
    inside = False
    skip_blank = False
    for line in text.splitlines(keepends=True):
        mark = line.strip()
        if mark == BEGIN:
            if inside:
                raise SystemExit(f"kit_only: {where}: nested {BEGIN}")
            inside = True
        elif mark == END:
            if not inside:
                raise SystemExit(f"kit_only: {where}: {END} without {BEGIN}")
            inside = False
            skip_blank = True
        elif inside:
            pass
        elif skip_blank and not mark:
            skip_blank = False
        else:
            skip_blank = False
            out.append(line)
    if inside:
        raise SystemExit(f"kit_only: {where}: {BEGIN} without {END}")
    return "".join(out)


def strip_key(text: str, where: str) -> str:
    """Cut the top-level `kit_resync` key, its body and the comment above it."""
    lines = text.splitlines(keepends=True)
    starts = [i for i, ln in enumerate(lines) if ln.startswith(KEY)]
    if not starts:
        return text
    if len(starts) > 1:
        raise SystemExit(f"kit_only: {where}: {KEY} appears {len(starts)} times")
    first = starts[0]
    while first > 0 and lines[first - 1].startswith("#"):
        first -= 1
    last = starts[0] + 1
    # The body is every following indented or blank line up to the next
    # top-level line; trailing blanks are handled below.
    while last < len(lines) and (lines[last][:1] in (" ", "\t") or not lines[last].strip()):
        last += 1
    while last > starts[0] + 1 and not lines[last - 1].strip():
        last -= 1
    if last < len(lines) and not lines[last].strip():
        last += 1
    elif last == len(lines) and first > 0 and not lines[first - 1].strip():
        first -= 1  # the key ended the file: drop the blank line before it
    return "".join(lines[:first] + lines[last:])


def cut_adr(root: Path) -> None:
    """Delete the kit-only ADR, its index row and the sentence in 0041 that points at it."""
    adr = root / "docs" / "decisions" / ADR
    if not adr.is_file():
        return
    adr.unlink()
    index = root / "docs" / "decisions" / "README.md"
    if index.is_file():
        lines = index.read_text(encoding="utf-8").splitlines(keepends=True)
        index.write_text("".join(ln for ln in lines if not ln.startswith(f"| [0051]({ADR})")), encoding="utf-8")
    path = root / ADR_0041
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        path.write_text(WIDENED.sub("", text, count=1), encoding="utf-8")
    left = sorted(p.relative_to(root).as_posix() for p in root.rglob("*")
                  if p.is_file() and ADR in p.read_text(encoding="utf-8", errors="replace"))
    if left:
        raise SystemExit(f"kit_only: {ADR} is cut but still named in: {', '.join(left)}")


def cut_test(root: Path) -> None:
    """Cut the sweep test that asserts the kit-only rule, its mutations, and one from the expected count."""
    path = root / SWEEP_TEST
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    n = text.count(TEST_TITLE)
    if n == 0:
        return
    if n > 1:
        raise SystemExit(f"kit_only: {SWEEP_TEST}: the ADR 0051 test appears {n} times")
    start = text.index(TEST_TITLE)
    if start and text[start - 1] != "\n":
        raise SystemExit(f"kit_only: {SWEEP_TEST}: the ADR 0051 test does not start a line")
    end = text.find("\n});\n", start)
    if end < 0:
        raise SystemExit(f"kit_only: {SWEEP_TEST}: the ADR 0051 test has no closing `}});` line")
    end += len("\n});\n")
    if text[end:end + 1] == "\n":
        end += 1  # the blank line after it
    text = text[:start] + text[end:]
    lines = text.splitlines(keepends=True)
    text = "".join(ln for ln in lines if not ln.startswith(tuple(f"  {k}: [worker, " for k in KIT_MUTATIONS)))
    for word in ("kit-only:", "kit_resync", "ADR 0051", *(f"{k}:" for k in KIT_MUTATIONS)):
        if word in text:
            raise SystemExit(f"kit_only: {SWEEP_TEST}: {word!r} is left after the ADR 0051 test is cut")
    path.write_text(text, encoding="utf-8")
    _count_down(root / RUN_TESTS)


def _count_down(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    head = "\ntest_prompt_audit_sweep() {\n"
    start = text.find(head)
    end = text.find("\n}\n", start) if start >= 0 else -1
    if start < 0 or end < 0:
        raise SystemExit(f"kit_only: {RUN_TESTS}: no test_prompt_audit_sweep() function")
    body = text[start:end]
    found = re.findall(r'"\$pass_n" == "(\d+)"', body)
    if len(found) != 1:
        raise SystemExit(f"kit_only: {RUN_TESTS}: test_prompt_audit_sweep() states its pass count {len(found)} times, not once")
    n = int(found[0])
    for form in COUNT_FORMS:
        old, new = form.format(n=n), form.format(n=n - 1)
        if body.count(old) != 1:
            raise SystemExit(f"kit_only: {RUN_TESTS}: expected 1 {old!r} in test_prompt_audit_sweep()")
        body = body.replace(old, new)
    path.write_text(text[:start] + body + text[end:], encoding="utf-8")


def apply(root: Path, ctx) -> None:
    routines = root / "docs" / "routines"
    for path in sorted(routines.glob("*.md")) if routines.is_dir() else []:
        text = path.read_text(encoding="utf-8")
        new = strip_blocks(text, path.relative_to(root).as_posix())
        if new != text:
            path.write_text(new, encoding="utf-8")
    path = root / "repos.yml"
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        new = strip_key(text, "repos.yml")
        if new != text:
            path.write_text(new, encoding="utf-8")
    cut_test(root)  # before cut_adr: the test names the ADR's file
    cut_adr(root)  # last: it checks nothing else names the ADR
